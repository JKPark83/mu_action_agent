"""LangGraph 노드 함수 – 동기 실행"""
from __future__ import annotations

import json
import logging

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.agent.prompts import (
    BID_PRICE_PROMPT,
    FINAL_RESPONSE_PROMPT,
    PARSE_INPUT_PROMPT,
    RIGHTS_ANALYSIS_PROMPT,
    SALE_ESTIMATE_PROMPT,
)
from src.agent.state import AgentState
from src.llm.provider import create_llm
from src.models.schemas import (
    AuctionCaseInput,
    BidRecommendation,
    CostBreakdown,
    FullAnalysisResult,
    MarketDataResponse,
    RightsAssessment,
    SalePriceEstimate,
)
from src.tools.real_estate_api import RealEstateAPIClient

logger = logging.getLogger(__name__)


def _get_llm(state: AgentState):
    """상태 또는 환경변수에서 LLM 인스턴스를 생성한다."""
    return create_llm()


# ---------------------------------------------------------------------------
# 1. parse_input – 사용자 입력을 AuctionCaseInput으로 구조화
# ---------------------------------------------------------------------------

def parse_input(state: AgentState) -> dict:
    last_msg = state["messages"][-1]

    try:
        llm = _get_llm(state)
    except ValueError as e:
        return {
            "messages": [AIMessage(content=f"LLM 설정 오류: {e}")],
            "error": str(e),
            "current_step": "error",
        }

    structured_llm = llm.with_structured_output(AuctionCaseInput)

    try:
        result: AuctionCaseInput = structured_llm.invoke([
            SystemMessage(content=PARSE_INPUT_PROMPT),
            HumanMessage(content=last_msg.content),
        ])
    except Exception as e:
        logger.warning("입력 파싱 실패: %s", e)
        return {
            "messages": [AIMessage(content=(
                "입력 정보를 파싱하지 못했습니다. "
                "다음 정보를 확인해 주세요: 소재지 주소, 감정가, 최저매각가격"
            ))],
            "error": "parse_failed",
            "current_step": "error",
        }

    return {
        "auction_case": result.model_dump(),
        "current_step": "parsed",
        "error": None,
    }


# ---------------------------------------------------------------------------
# 2. router – MVP에서는 항상 "all"
# ---------------------------------------------------------------------------

def router(state: AgentState) -> dict:
    if state.get("error"):
        return {"route": "need_more_info", "current_step": "routing"}
    if not state.get("auction_case"):
        return {"route": "need_more_info", "current_step": "routing"}
    return {"route": "all", "current_step": "routing"}


def route_decision(state: AgentState) -> str:
    return state.get("route", "all")


# ---------------------------------------------------------------------------
# 3. fetch_market_data – 국토부 API 호출
# ---------------------------------------------------------------------------

def fetch_market_data(state: AgentState) -> dict:
    case = state["auction_case"]
    if not case:
        return {"market_data": None, "current_step": "market_data"}

    client = RealEstateAPIClient()
    try:
        result = client.get_recent_transactions(
            property_type=case["property_type"],
            address=case["address"],
            months=6,
        )
    finally:
        client.close()

    return {
        "market_data": result.model_dump(),
        "current_step": "market_data",
    }


# ---------------------------------------------------------------------------
# 4. analyze_bid_price – 입찰가 산출
# ---------------------------------------------------------------------------

def analyze_bid_price(state: AgentState) -> dict:
    case = state["auction_case"]
    market = state.get("market_data")
    if not case:
        return {"current_step": "bid_price"}

    appraisal = case["appraisal_value"]
    minimum_bid = case["minimum_bid"]
    area = case.get("area_m2") or 0

    # 시세 기반 추정가
    avg_per_m2 = (market or {}).get("avg_price_per_m2", 0)
    if avg_per_m2 > 0 and area > 0:
        market_estimate = avg_per_m2 * area
    else:
        market_estimate = appraisal  # 시세 없으면 감정가 사용

    # 기본 범위
    base_min = int(market_estimate * 0.70)
    base_max = int(market_estimate * 0.85)

    # 최저가 보장
    bid_min = max(base_min, minimum_bid)
    bid_max = max(base_max, minimum_bid)
    optimal = (bid_min + bid_max) // 2

    appraisal_ratio = round(optimal / appraisal, 4) if appraisal else 0
    market_ratio = round(optimal / market_estimate, 4) if market_estimate else 0

    # LLM 정성 분석
    reasoning = _llm_bid_reasoning(state, case, market, bid_min, bid_max, optimal)

    bid_rec = BidRecommendation(
        min_bid=bid_min,
        max_bid=bid_max,
        optimal_bid=optimal,
        appraisal_ratio=appraisal_ratio,
        market_ratio=market_ratio,
        reasoning=reasoning,
    )

    # analysis_result 부분 업데이트용으로 별도 저장
    current = state.get("analysis_result") or {}
    current["bid_recommendation"] = bid_rec.model_dump()

    return {
        "analysis_result": current,
        "current_step": "bid_price",
    }


def _llm_bid_reasoning(state, case, market, bid_min, bid_max, optimal) -> str:
    try:
        llm = _get_llm(state)
        content = (
            f"경매 물건 정보:\n{json.dumps(case, ensure_ascii=False)}\n\n"
            f"시세 데이터:\n{json.dumps(market, ensure_ascii=False) if market else '없음'}\n\n"
            f"계산된 입찰가 범위: {bid_min:,}원 ~ {bid_max:,}원, 최적: {optimal:,}원\n\n"
            "위 수치를 바탕으로 입찰가 산출 근거를 설명하세요."
        )
        resp = llm.invoke([
            SystemMessage(content=BID_PRICE_PROMPT),
            HumanMessage(content=content),
        ])
        return resp.content
    except Exception as e:
        logger.warning("입찰가 LLM 분석 실패: %s", e)
        return f"입찰가 범위 {bid_min:,}~{bid_max:,}원 (시세 또는 감정가 기반 산출)"


# ---------------------------------------------------------------------------
# 5. analyze_rights – 권리분석
# ---------------------------------------------------------------------------

def analyze_rights(state: AgentState) -> dict:
    case = state["auction_case"]
    if not case:
        return {"current_step": "rights"}

    rights = case.get("rights", [])
    if not rights:
        assessment = RightsAssessment(
            risk_grade="A",
            risk_grade_label="안전",
            summary="입력된 권리관계가 없습니다. 등기부등본을 확인하세요.",
            total_assumed_amount=0,
            details=[],
            recommendations=["등기부등본 열람을 통해 실제 권리관계를 확인하세요."],
        )
    else:
        assessment = _llm_rights_analysis(state, case)

    current = state.get("analysis_result") or {}
    current["rights_assessment"] = assessment.model_dump()

    return {
        "analysis_result": current,
        "current_step": "rights",
    }


def _llm_rights_analysis(state, case) -> RightsAssessment:
    try:
        llm = _get_llm(state)
        structured = llm.with_structured_output(RightsAssessment)
        content = (
            f"경매 물건 주소: {case['address']}\n"
            f"권리관계 목록:\n{json.dumps(case.get('rights', []), ensure_ascii=False, indent=2)}"
        )
        return structured.invoke([
            SystemMessage(content=RIGHTS_ANALYSIS_PROMPT),
            HumanMessage(content=content),
        ])
    except Exception as e:
        logger.warning("권리분석 LLM 실패: %s", e)
        return RightsAssessment(
            risk_grade="B",
            risk_grade_label="주의",
            summary="AI 권리분석에 실패했습니다. 전문가 상담을 권합니다.",
            total_assumed_amount=0,
            details=[],
            recommendations=["법무사 또는 변호사 상담을 통해 권리분석을 받으세요."],
        )


# ---------------------------------------------------------------------------
# 6. estimate_sale_price – 매도가/비용/수익률
# ---------------------------------------------------------------------------

def estimate_sale_price(state: AgentState) -> dict:
    case = state["auction_case"]
    market = state.get("market_data")
    current = state.get("analysis_result") or {}

    if not case:
        return {"analysis_result": current, "current_step": "sale_estimate"}

    # 시세 추정가
    avg_per_m2 = (market or {}).get("avg_price_per_m2", 0)
    area = case.get("area_m2") or 0
    if avg_per_m2 > 0 and area > 0:
        market_est = avg_per_m2 * area
    else:
        market_est = case["appraisal_value"]

    optimistic = int(market_est * 0.95)
    realistic = int(market_est * 0.92)
    conservative = int(market_est * 0.88)

    # 낙찰 예정가 = 추천 최적가 또는 최저가
    bid_rec = current.get("bid_recommendation", {})
    bid_price = bid_rec.get("optimal_bid") or case["minimum_bid"]

    # 취득세 (간이 계산)
    if bid_price <= 600_000_000:
        acq_tax_rate = 0.01
    elif bid_price <= 900_000_000:
        acq_tax_rate = 0.02
    else:
        acq_tax_rate = 0.03
    acquisition_tax = int(bid_price * acq_tax_rate)
    registration_fee = int(bid_price * 0.002)

    # 임차인 유무 → 명도비
    rights = case.get("rights", [])
    has_tenant = any(r.get("type") in ("임차인", "전세권") for r in rights)
    eviction_cost = 3_000_000 if has_tenant else 0

    repair = 5_000_000

    # 양도세 (1년 미만 70%)
    gross_profit = realistic - bid_price
    total_costs_before_tax = acquisition_tax + registration_fee + eviction_cost + repair
    taxable = max(gross_profit - total_costs_before_tax, 0)
    cgt = int(taxable * 0.70)  # 단기보유

    costs = CostBreakdown(
        acquisition_tax=acquisition_tax,
        registration_fee=registration_fee,
        eviction_cost=eviction_cost,
        repair_estimate=repair,
        capital_gains_tax_estimate=cgt,
    )

    net_profit = realistic - bid_price - costs.total
    total_investment = bid_price + costs.total
    roi = round(net_profit / total_investment * 100, 2) if total_investment else 0

    sale_est = SalePriceEstimate(
        optimistic=optimistic,
        realistic=realistic,
        conservative=conservative,
        costs=costs,
        net_profit_estimate=net_profit,
        roi_percent=roi,
    )

    current["sale_estimate"] = sale_est.model_dump()

    return {
        "analysis_result": current,
        "current_step": "sale_estimate",
    }


# ---------------------------------------------------------------------------
# 7. synthesize – 종합 결과 조립
# ---------------------------------------------------------------------------

def synthesize(state: AgentState) -> dict:
    case_data = state.get("auction_case") or {}
    market_data = state.get("market_data")
    current = state.get("analysis_result") or {}

    case_input = AuctionCaseInput(**case_data) if case_data else None

    result = FullAnalysisResult(
        auction_case=case_input or AuctionCaseInput(
            property_type="아파트", address="N/A",
            appraisal_value=1, minimum_bid=1,
        ),
        market_data=MarketDataResponse(**market_data) if market_data else None,
        bid_recommendation=(
            BidRecommendation(**current["bid_recommendation"])
            if current.get("bid_recommendation") else None
        ),
        sale_estimate=(
            SalePriceEstimate(**current["sale_estimate"])
            if current.get("sale_estimate") else None
        ),
        rights_assessment=(
            RightsAssessment(**current["rights_assessment"])
            if current.get("rights_assessment") else None
        ),
    )

    return {
        "analysis_result": result.model_dump(),
        "current_step": "synthesized",
    }


# ---------------------------------------------------------------------------
# 8. respond – 최종 응답 생성
# ---------------------------------------------------------------------------

def respond(state: AgentState) -> dict:
    # 에러/추가정보 필요 시 이미 메시지가 있으면 패스
    if state.get("error"):
        return {"current_step": "done"}

    analysis = state.get("analysis_result")
    if not analysis:
        return {
            "messages": [AIMessage(content="분석 결과를 생성하지 못했습니다.")],
            "current_step": "done",
        }

    try:
        llm = _get_llm(state)
        content = (
            f"분석 결과 JSON:\n{json.dumps(analysis, ensure_ascii=False, indent=2)}"
        )
        resp = llm.invoke([
            SystemMessage(content=FINAL_RESPONSE_PROMPT),
            HumanMessage(content=content),
        ])
        return {
            "messages": [AIMessage(content=resp.content)],
            "current_step": "done",
        }
    except Exception as e:
        logger.warning("최종 응답 생성 실패: %s", e)
        # 폴백: JSON 요약
        return {
            "messages": [AIMessage(content=_fallback_response(analysis))],
            "current_step": "done",
        }


def _fallback_response(analysis: dict) -> str:
    """LLM 없이 분석 결과를 텍스트로 요약"""
    lines = ["## 경매 분석 결과\n"]

    case = analysis.get("auction_case", {})
    lines.append(f"**물건**: {case.get('address', 'N/A')}")
    lines.append(f"**종류**: {case.get('property_type', 'N/A')}")
    lines.append(f"**감정가**: {case.get('appraisal_value', 0):,}원")
    lines.append(f"**최저가**: {case.get('minimum_bid', 0):,}원\n")

    bid = analysis.get("bid_recommendation")
    if bid:
        lines.append("### 추천 입찰가")
        lines.append(f"- 최저: {bid['min_bid']:,}원")
        lines.append(f"- 최적: {bid['optimal_bid']:,}원")
        lines.append(f"- 최고: {bid['max_bid']:,}원\n")

    rights = analysis.get("rights_assessment")
    if rights:
        lines.append(f"### 권리분석 리스크: {rights['risk_grade']} ({rights['risk_grade_label']})")
        lines.append(f"{rights['summary']}\n")

    sale = analysis.get("sale_estimate")
    if sale:
        lines.append("### 매도가 추정")
        lines.append(f"- 현실적 매도가: {sale['realistic']:,}원")
        lines.append(f"- 순수익 추정: {sale['net_profit_estimate']:,}원")
        lines.append(f"- 수익률: {sale['roi_percent']}%\n")

    disclaimers = analysis.get("disclaimers", [])
    if disclaimers:
        lines.append("---")
        lines.append("**[면책 고지]**")
        for d in disclaimers:
            lines.append(f"- {d}")

    return "\n".join(lines)
