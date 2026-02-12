"""보고서 생성 에이전트 노드 - 최종 분석 보고서 작성"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict

from anthropic import AsyncAnthropic

from app.agents.prompts.report_prompts import REPORT_PROMPT
from app.agents.state import AgentState
from app.config import settings

logger = logging.getLogger(__name__)

_client: AsyncAnthropic | None = None


def _get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        _client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


def _parse_json_response(text: str) -> dict:
    """LLM 응답에서 JSON을 추출한다."""
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        return json.loads(match.group(1).strip())
    return json.loads(text.strip())


async def _call_llm(prompt: str, max_tokens: int = 4096) -> str:
    """Anthropic Claude API를 호출한다."""
    client = _get_client()
    response = await client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def _safe_dict(obj: object) -> str:
    """dataclass 객체를 JSON 문자열로 변환한다. None이면 '없음' 반환."""
    if obj is None:
        return "없음"
    try:
        return json.dumps(asdict(obj), ensure_ascii=False, default=str)[:3000]
    except Exception:
        return str(obj)[:3000]


async def report_generator_node(state: AgentState) -> AgentState:
    """보고서 생성 에이전트 노드.

    처리 흐름:
    1. 모든 분석 결과를 수집
    2. Claude로 사용자 친화적 리포트 텍스트 생성
    3. 최종 report dict 생성하여 state에 저장
    """
    errors: list[str] = list(state.errors)

    try:
        prompt = REPORT_PROMPT.format(
            rights=_safe_dict(state.rights_analysis),
            market=_safe_dict(state.market_data),
            news=_safe_dict(state.news_analysis),
            valuation=_safe_dict(state.valuation),
        )

        raw = await _call_llm(prompt, max_tokens=3000)
        analysis_summary = _parse_json_response(raw)

        # 최종 리포트 조합
        report: dict = {
            "analysis_summary": analysis_summary,
        }

        # 가치평가 결과 포함
        if state.valuation:
            try:
                report["valuation"] = asdict(state.valuation)
            except Exception:
                pass

        # 권리분석 결과 포함
        if state.rights_analysis:
            try:
                report["rights_analysis"] = asdict(state.rights_analysis)
            except Exception:
                pass

        # 시장 데이터 포함
        if state.market_data:
            try:
                report["market_data"] = asdict(state.market_data)
            except Exception:
                pass

        # 뉴스 분석 포함
        if state.news_analysis:
            try:
                report["news_analysis"] = asdict(state.news_analysis)
            except Exception:
                pass

        logger.info("보고서 생성 완료")
        state.report = report

    except Exception as exc:
        logger.exception("보고서 생성 오류")
        errors.append(f"보고서 생성 오류: {exc}")
        state.report = {"error": str(exc), "partial": True}

    state.errors = errors
    return state
