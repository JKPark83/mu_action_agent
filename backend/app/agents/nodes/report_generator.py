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


def _fix_json(text: str) -> str:
    """LLM이 생성한 JSON의 흔한 오류를 수정한다."""
    return re.sub(r",\s*([}\]])", r"\1", text)


def _try_parse(raw: str) -> dict:
    """JSON 파싱을 시도하고, 실패하면 흔한 오류를 수정 후 재시도한다."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return json.loads(_fix_json(raw))


def _parse_json_response(text: str) -> dict:
    """LLM 응답에서 JSON을 추출한다."""
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        return _try_parse(match.group(1).strip())
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        return _try_parse(match.group(0))
    return _try_parse(text.strip())


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


async def report_generator_node(state: AgentState) -> dict:
    """보고서 생성 에이전트 노드.

    처리 흐름:
    1. 모든 분석 결과를 수집
    2. Claude로 사용자 친화적 리포트 텍스트 생성
    3. 최종 report dict를 partial dict로 반환
    """
    new_errors: list[str] = []

    try:
        prompt = REPORT_PROMPT.format(
            rights=_safe_dict(state.get("rights_analysis")),
            market=_safe_dict(state.get("market_data")),
            news=_safe_dict(state.get("news_analysis")),
            valuation=_safe_dict(state.get("valuation")),
        )

        raw = await _call_llm(prompt, max_tokens=3000)
        analysis_summary = _parse_json_response(raw)

        # 최종 리포트 조합: 프론트엔드가 기대하는 구조에 맞춰 생성
        report: dict = {
            "analysis_summary": analysis_summary,
        }

        # 가치평가 결과를 report 최상위 레벨로 플래튼
        valuation = state.get("valuation")
        if valuation:
            try:
                val = asdict(valuation)
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

        # 시세 차트 데이터 (월별 평균가에서 추출)
        market_data = state.get("market_data")
        if market_data:
            try:
                md = asdict(market_data)
                chart_data: dict = {}
                if md.get("monthly_averages"):
                    chart_data["price_trend"] = [
                        {"date": m["date"], "price": m["price"]}
                        for m in md["monthly_averages"]
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
        result_dict: dict = {"report": report}

    except Exception as exc:
        logger.exception("보고서 생성 오류")
        new_errors.append(f"보고서 생성 오류: {exc}")
        result_dict = {"report": {"error": str(exc), "partial": True}}

    if new_errors:
        result_dict["errors"] = new_errors
    return result_dict
