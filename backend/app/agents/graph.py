"""LangGraph StateGraph 워크플로우 정의

문서파싱 → [권리분석 | 시세분석 | 뉴스분석] (병렬) → 가치평가 → 보고서 생성
"""

from __future__ import annotations

import logging
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Any

from langgraph.graph import END, START, StateGraph
from langgraph.types import RetryPolicy

from app.agents.nodes.document_parser import document_parser_node
from app.agents.nodes.market_data import market_data_node
from app.agents.nodes.news_analysis import news_analysis_node
from app.agents.nodes.report_generator import report_generator_node
from app.agents.nodes.rights_analysis import rights_analysis_node
from app.agents.nodes.valuation import valuation_node
from app.agents.state import AgentState
from app.api.websocket.manager import manager
from app.database import async_session
from app.migrations import extract_summary_fields
from app.models.analysis import Analysis, AnalysisStatus

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# RetryPolicy 정의 (기존 _run_node_with_retry의 3-attempt 지수백오프를 대체)
# ---------------------------------------------------------------------------

retry_policy = RetryPolicy(
    initial_interval=1.0,
    backoff_factor=2.0,
    max_interval=128.0,
    max_attempts=3,
)

# ---------------------------------------------------------------------------
# 노드 이름 상수 (WebSocket 진행도 매핑용)
# ---------------------------------------------------------------------------

WORKFLOW_NODES: list[str] = [
    "document_parser",
    "rights_analysis",
    "market_data",
    "news_analysis",
    "valuation",
    "report_generator",
]

PARALLEL_NODES: list[str] = ["rights_analysis", "market_data", "news_analysis"]


# ---------------------------------------------------------------------------
# StateGraph 구성
# ---------------------------------------------------------------------------


def build_graph() -> StateGraph:
    """StateGraph를 구성하고 컴파일된 그래프를 반환한다."""
    graph = StateGraph(AgentState)

    # 노드 등록
    graph.add_node("document_parser", document_parser_node, retry_policy=retry_policy)
    graph.add_node("rights_analysis", rights_analysis_node, retry_policy=retry_policy)
    graph.add_node("market_data", market_data_node, retry_policy=retry_policy)
    graph.add_node("news_analysis", news_analysis_node, retry_policy=retry_policy)
    graph.add_node("valuation", valuation_node, retry_policy=retry_policy)
    graph.add_node("report_generator", report_generator_node, retry_policy=retry_policy)

    # 엣지 정의
    graph.add_edge(START, "document_parser")

    # Fan-out: document_parser → 3개 병렬 노드
    graph.add_edge("document_parser", "rights_analysis")
    graph.add_edge("document_parser", "market_data")
    graph.add_edge("document_parser", "news_analysis")

    # Fan-in: 3개 병렬 노드 → valuation
    graph.add_edge("rights_analysis", "valuation")
    graph.add_edge("market_data", "valuation")
    graph.add_edge("news_analysis", "valuation")

    # Sequential
    graph.add_edge("valuation", "report_generator")
    graph.add_edge("report_generator", END)

    return graph.compile()


# 모듈 레벨에서 컴파일 (앱 시작 시 한 번만)
compiled_graph = build_graph()


# ---------------------------------------------------------------------------
# 워크플로우 실행
# ---------------------------------------------------------------------------


async def run_analysis_workflow(
    analysis_id: str,
    file_paths: list[str] | None = None,
) -> None:
    """분석 워크플로우를 실행한다 (BackgroundTask에서 호출).

    astream(stream_mode="updates")로 각 노드 완료 시 WebSocket 알림을 전송한다.
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

    # 초기 상태 (모든 필드에 기본값 제공)
    initial_state: AgentState = {
        "analysis_id": analysis_id,
        "file_paths": file_paths,
        "registry": None,
        "appraisal": None,
        "sale_item": None,
        "status_report": None,
        "rights_analysis": None,
        "market_data": None,
        "news_analysis": None,
        "valuation": None,
        "report": None,
        "errors": [],
    }

    try:
        # astream으로 노드 완료를 추적하며 WebSocket 진행도 전송
        completed: set[str] = set()
        final_state: dict[str, Any] = dict(initial_state)

        await _send_progress(analysis_id, "document_parser", "running", 0)

        async for event in compiled_graph.astream(
            initial_state,
            stream_mode="updates",
        ):
            for node_name, updates in event.items():
                if node_name not in _NODE_STAGES:
                    continue

                completed.add(node_name)
                await _send_progress(analysis_id, node_name, "done", 100)

                # 다음 단계 running 신호 전송
                if node_name == "document_parser":
                    for p in PARALLEL_NODES:
                        await _send_progress(analysis_id, p, "running", 0)
                elif node_name in PARALLEL_NODES and all(p in completed for p in PARALLEL_NODES):
                    await _send_progress(analysis_id, "valuation", "running", 0)
                elif node_name == "valuation":
                    await _send_progress(analysis_id, "report_generator", "running", 0)

                # final_state 갱신 (errors는 reducer가 처리하므로 별도 누적)
                if isinstance(updates, dict):
                    for key, value in updates.items():
                        if key == "errors":
                            final_state.setdefault("errors", [])
                            final_state["errors"].extend(value)
                        else:
                            final_state[key] = value

        # DB: 결과 저장
        state_report = final_state.get("report")
        final_status = AnalysisStatus.DONE if state_report else AnalysisStatus.ERROR

        parsed_docs: dict = {}
        if final_state.get("registry"):
            parsed_docs["registry"] = _to_json(final_state["registry"])
        if final_state.get("appraisal"):
            parsed_docs["appraisal"] = _to_json(final_state["appraisal"])
        if final_state.get("sale_item"):
            parsed_docs["sale_item"] = _to_json(final_state["sale_item"])

        errors = final_state.get("errors", [])

        async with async_session() as db:
            analysis = await db.get(Analysis, analysis_id)
            if analysis:
                analysis.status = final_status
                analysis.completed_at = datetime.now(timezone.utc)
                analysis.parsed_documents = parsed_docs if parsed_docs else None
                analysis.report = state_report
                analysis.rights_analysis = _to_json(final_state.get("rights_analysis"))
                analysis.market_data = _to_json(final_state.get("market_data"))
                analysis.news_analysis = _to_json(final_state.get("news_analysis"))
                analysis.valuation = _to_json(final_state.get("valuation"))
                analysis.errors = errors if errors else None
                extract_summary_fields(analysis)
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
# 헬퍼
# ---------------------------------------------------------------------------

# 노드 이름 집합 (WebSocket 진행도 대상)
_NODE_STAGES: set[str] = set(WORKFLOW_NODES)


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
