"""LangGraph 워크플로우 정의

문서파싱 → [권리분석 | 시세분석 | 뉴스분석] (병렬) → 가치평가 → 보고서 생성
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any, Callable, Coroutine

from app.agents.nodes.document_parser import document_parser_node
from app.agents.nodes.market_data import market_data_node
from app.agents.nodes.news_analysis import news_analysis_node
from app.agents.nodes.report_generator import report_generator_node
from app.agents.nodes.rights_analysis import rights_analysis_node
from app.agents.nodes.valuation import valuation_node
from app.agents.state import AgentState
from app.api.websocket.manager import manager
from app.database import async_session
from app.models.analysis import Analysis, AnalysisStatus

logger = logging.getLogger(__name__)

# 노드 타입 정의
NodeFunc = Callable[[AgentState], Coroutine[Any, Any, AgentState]]

# 워크플로우 노드 정의 (실행 순서)
WORKFLOW_NODES: list[str] = [
    "document_parser",
    "rights_analysis",
    "market_data",
    "news_analysis",
    "valuation",
    "report_generator",
]

# 노드 이름 → 함수 매핑
NODE_REGISTRY: dict[str, NodeFunc] = {
    "document_parser": document_parser_node,
    "rights_analysis": rights_analysis_node,
    "market_data": market_data_node,
    "news_analysis": news_analysis_node,
    "valuation": valuation_node,
    "report_generator": report_generator_node,
}

# 병렬 실행 그룹 (document_parser 이후 동시 실행)
PARALLEL_NODES = ["rights_analysis", "market_data", "news_analysis"]


# ---------------------------------------------------------------------------
# 에러 래퍼 (재시도 포함)
# ---------------------------------------------------------------------------


async def _run_node_with_retry(
    name: str,
    func: NodeFunc,
    state: AgentState,
    max_retries: int = 3,
) -> AgentState:
    """노드를 실행하고 실패 시 지수 백오프로 재시도한다."""
    for attempt in range(max_retries):
        try:
            return await func(state)
        except Exception as exc:
            if attempt == max_retries - 1:
                logger.exception("%s 노드 최종 실패 (%d회 시도)", name, max_retries)
                state.errors = list(state.errors) + [f"{name} 실패: {exc}"]
                return state
            wait = 2 ** attempt
            logger.warning("%s 노드 실패 (시도 %d/%d), %ds 후 재시도: %s", name, attempt + 1, max_retries, wait, exc)
            await asyncio.sleep(wait)
    return state


# ---------------------------------------------------------------------------
# 워크플로우 실행
# ---------------------------------------------------------------------------


async def run_analysis_workflow(
    analysis_id: str,
    file_paths: list[str] | None = None,
) -> None:
    """분석 워크플로우를 실행한다 (BackgroundTask에서 호출).

    실행 순서:
    1. DB 상태를 running으로 업데이트
    2. document_parser 실행
    3. [rights_analysis, market_data, news_analysis] 병렬 실행
    4. valuation 실행
    5. report_generator 실행
    6. DB에 결과 저장 + 상태를 done/error로 업데이트
    7. WebSocket 완료 알림
    """
    # DB: status → running, 파일 경로 조회
    async with async_session() as db:
        analysis = await db.get(Analysis, analysis_id)
        if analysis is None:
            logger.error("analysis not found: %s", analysis_id)
            return
        analysis.status = AnalysisStatus.RUNNING
        analysis.started_at = datetime.now(timezone.utc)
        await db.commit()

        # file_paths가 없으면 DB에서 업로드된 파일 경로를 조회
        if not file_paths:
            from sqlalchemy import select
            from app.models.file import UploadedFile

            result = await db.execute(
                select(UploadedFile.stored_path).where(
                    UploadedFile.analysis_id == analysis_id
                )
            )
            file_paths = [row[0] for row in result.all()]

    if not file_paths:
        logger.error("분석할 파일이 없습니다: %s", analysis_id)
        async with async_session() as db:
            analysis = await db.get(Analysis, analysis_id)
            if analysis:
                analysis.status = AnalysisStatus.ERROR
                analysis.completed_at = datetime.now(timezone.utc)
                analysis.errors = ["분석할 PDF 파일이 없습니다."]
                await db.commit()
        await manager.send_progress(analysis_id, {
            "type": "analysis_error",
            "error": "분석할 PDF 파일이 없습니다.",
        })
        return

    # 초기 상태
    state = AgentState(
        analysis_id=analysis_id,
        file_paths=file_paths,
    )

    await _send_progress(analysis_id, "document_parser", "running", 0)

    try:
        # 1) 문서 파싱
        state = await _run_node_with_retry("document_parser", document_parser_node, state)
        await _send_progress(analysis_id, "document_parser", "done", 100)

        # 2) 병렬 분석 (권리/시세/뉴스)
        for name in PARALLEL_NODES:
            await _send_progress(analysis_id, name, "running", 0)

        async def _run_parallel_node(name: str) -> None:
            nonlocal state
            # 병렬 노드는 state를 공유하지만 각각 다른 필드를 수정하므로 안전
            await _run_node_with_retry(name, NODE_REGISTRY[name], state)

        await asyncio.gather(
            _run_parallel_node("rights_analysis"),
            _run_parallel_node("market_data"),
            _run_parallel_node("news_analysis"),
        )

        for name in PARALLEL_NODES:
            await _send_progress(analysis_id, name, "done", 100)

        # 3) 가치 평가
        await _send_progress(analysis_id, "valuation", "running", 0)
        state = await _run_node_with_retry("valuation", valuation_node, state)
        await _send_progress(analysis_id, "valuation", "done", 100)

        # 4) 보고서 생성
        await _send_progress(analysis_id, "report_generator", "running", 0)
        state = await _run_node_with_retry("report_generator", report_generator_node, state)
        await _send_progress(analysis_id, "report_generator", "done", 100)

        # DB: 결과 저장
        final_status = AnalysisStatus.DONE if state.report else AnalysisStatus.ERROR

        # parsed_documents 조합
        parsed_docs: dict = {}
        if state.registry:
            parsed_docs["registry"] = _to_json(state.registry)
        if state.appraisal:
            parsed_docs["appraisal"] = _to_json(state.appraisal)
        if state.sale_item:
            parsed_docs["sale_item"] = _to_json(state.sale_item)

        async with async_session() as db:
            analysis = await db.get(Analysis, analysis_id)
            if analysis:
                analysis.status = final_status
                analysis.completed_at = datetime.now(timezone.utc)
                analysis.parsed_documents = parsed_docs if parsed_docs else None
                analysis.report = state.report
                analysis.rights_analysis = _to_json(state.rights_analysis)
                analysis.market_data = _to_json(state.market_data)
                analysis.news_analysis = _to_json(state.news_analysis)
                analysis.valuation = _to_json(state.valuation)
                analysis.errors = state.errors if state.errors else None
                await db.commit()

        # WebSocket 완료 알림
        await manager.send_progress(analysis_id, {
            "type": "analysis_complete",
            "status": final_status.value,
            "report_url": f"/api/v1/analyses/{analysis_id}/report",
        })

    except Exception as exc:
        logger.exception("워크플로우 치명 오류: %s", analysis_id)
        async with async_session() as db:
            analysis = await db.get(Analysis, analysis_id)
            if analysis:
                analysis.status = AnalysisStatus.ERROR
                analysis.completed_at = datetime.now(timezone.utc)
                analysis.errors = [str(exc)]
                await db.commit()

        await manager.send_progress(analysis_id, {
            "type": "analysis_error",
            "error": str(exc),
        })


# ---------------------------------------------------------------------------
# 헬퍼 함수
# ---------------------------------------------------------------------------


def _to_json(obj: Any) -> dict | None:
    """dataclass를 JSON-serializable dict로 변환한다."""
    if obj is None:
        return None
    try:
        return asdict(obj)
    except Exception:
        return None


async def _send_progress(
    analysis_id: str,
    stage: str,
    status: str,
    progress: int,
) -> None:
    """WebSocket으로 진행 상태를 전송한다."""
    await manager.send_progress(analysis_id, {
        "type": "status_update",
        "stage": stage,
        "status": status,
        "progress": progress,
    })
