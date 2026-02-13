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

        # 최종 리포트 조합: 프론트엔드가 기대하는 구조에 맞춰 생성
        # 프론트엔드 AnalysisReport 타입:
        #   recommendation, reasoning, risk_summary,
        #   bid_price, sale_price, expected_roi,
        #   cost_breakdown, confidence_score, disclaimer, chart_data
        report: dict = {
            "analysis_summary": analysis_summary,
        }

        # 가치평가 결과를 report 최상위 레벨로 플래튼
        if state.valuation:
            try:
                val = asdict(state.valuation)
                report["recommendation"] = val.get("recommendation", "hold")
                report["reasoning"] = val.get("reasoning", "")
                report["risk_summary"] = val.get("risk_summary", "")
                report["bid_price"] = val.get("bid_price", {})
                report["sale_price"] = val.get("sale_price", {})
                report["expected_roi"] = val.get("expected_roi", 0)
                report["cost_breakdown"] = val.get("cost_breakdown", {})
                report["confidence_score"] = val.get("confidence_score", 0)
                report["valuation"] = val
            except Exception:
                pass

        # 시세 차트 데이터 (시장 데이터에서 추출)
        if state.market_data:
            try:
                md = asdict(state.market_data)
                chart_data: dict = {}
                if md.get("recent_transactions"):
                    chart_data["price_trend"] = [
                        {"date": t.get("date", ""), "price": t.get("price", 0)}
                        for t in md["recent_transactions"][:20]
                    ]
                report["chart_data"] = chart_data
            except Exception:
                pass

        # 면책 조항
        report["disclaimer"] = (
            "본 분석은 AI가 생성한 참고 자료이며, 실제 투자 결정 시 "
            "법률·세무 전문가의 자문을 별도로 받으시기 바랍니다."
        )

        logger.info("보고서 생성 완료")
        state.report = report

    except Exception as exc:
        logger.exception("보고서 생성 오류")
        errors.append(f"보고서 생성 오류: {exc}")
        state.report = {"error": str(exc), "partial": True}

    state.errors = errors
    return state
