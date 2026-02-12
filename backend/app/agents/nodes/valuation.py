"""가치평가 에이전트 노드 - 입찰가, 매도가, ROI 산출"""

from __future__ import annotations

import logging

from app.agents.state import AgentState
from app.schemas.rights import RiskLevel
from app.schemas.valuation import (
    CostBreakdown,
    PriceRange,
    Recommendation,
    ValuationResult,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 1. 취득세 계산
# ---------------------------------------------------------------------------


def calculate_acquisition_tax(
    price: int,
    property_type: str,
    num_houses: int = 1,
) -> int:
    """취득세를 산출한다.

    주택 1채 기준:
    - 6억 이하: 1%
    - 6~9억: 1~3% (구간별 누진)
    - 9억 초과: 3%
    상가/오피스텔: 4.6%, 토지: 4%
    """
    if property_type in ("상가", "오피스텔"):
        rate = 0.046
    elif property_type == "토지":
        rate = 0.04
    elif num_houses >= 3:
        rate = 0.08
    elif num_houses == 2:
        rate = 0.08
    else:
        # 1주택
        if price <= 600_000_000:
            rate = 0.01
        elif price <= 900_000_000:
            rate = 0.01 + (price - 600_000_000) / 300_000_000 * 0.02
        else:
            rate = 0.03

    return int(price * rate)


# ---------------------------------------------------------------------------
# 2. 비용 산출
# ---------------------------------------------------------------------------


def estimate_eviction_cost(num_tenants: int, has_opposition: bool) -> int:
    """명도 비용을 추정한다. 대항력 있으면 500만원/인, 없으면 200만원/인."""
    per_tenant = 5_000_000 if has_opposition else 2_000_000
    return num_tenants * per_tenant


def calculate_cost_breakdown(
    bid_price: int,
    property_type: str,
    assumed_rights_cost: int,
    num_tenants: int,
    has_opposition_tenants: bool,
) -> CostBreakdown:
    """전체 비용을 산출한다."""
    acq_tax = calculate_acquisition_tax(bid_price, property_type)
    reg_fee = int(acq_tax * 0.2)
    legal_fee = 800_000
    eviction = estimate_eviction_cost(num_tenants, has_opposition_tenants)
    brokerage = int(bid_price * 0.004)

    return CostBreakdown(
        acquisition_tax=acq_tax,
        registration_fee=reg_fee,
        legal_fee=legal_fee,
        eviction_cost=eviction,
        repair_cost=0,
        capital_gains_tax=0,
    )


def total_cost(cost: CostBreakdown) -> int:
    """CostBreakdown의 모든 항목을 합산한다."""
    return (
        cost.acquisition_tax
        + cost.registration_fee
        + cost.legal_fee
        + cost.eviction_cost
        + cost.repair_cost
        + cost.capital_gains_tax
    )


# ---------------------------------------------------------------------------
# 3. 입찰 적정가 산출
# ---------------------------------------------------------------------------


def calculate_bid_price_range(
    estimated_market_value: int,
    assumed_rights_cost: int,
    extra_cost: int,
    minimum_bid: int,
) -> PriceRange:
    """입찰 적정가를 3단계(보수적/적정/공격적)로 산출한다."""
    deduction = assumed_rights_cost + extra_cost
    conservative = int(estimated_market_value * 0.65) - deduction
    moderate = int(estimated_market_value * 0.75) - deduction
    aggressive = int(estimated_market_value * 0.85) - deduction

    return PriceRange(
        conservative=max(conservative, minimum_bid),
        moderate=max(moderate, minimum_bid),
        aggressive=max(aggressive, minimum_bid),
    )


# ---------------------------------------------------------------------------
# 4. 매도 적정가 산출
# ---------------------------------------------------------------------------


def calculate_sale_price_range(
    market_value: int,
    price_trend_direction: str,
    has_positive_factors: bool,
    has_negative_factors: bool,
) -> PriceRange:
    """매도 적정가를 3단계(비관/기본/낙관)로 산출한다."""
    trend_adj = 0.0
    if price_trend_direction == "상승":
        trend_adj = 0.03
    elif price_trend_direction == "하락":
        trend_adj = -0.03

    factor_adj = 0.0
    if has_positive_factors:
        factor_adj += 0.02
    if has_negative_factors:
        factor_adj -= 0.02

    return PriceRange(
        conservative=int(market_value * (0.95 + trend_adj + factor_adj)),
        moderate=int(market_value * (1.00 + trend_adj + factor_adj)),
        aggressive=int(market_value * (1.07 + trend_adj + factor_adj)),
    )


# ---------------------------------------------------------------------------
# 5. 수익률 분석
# ---------------------------------------------------------------------------


def calculate_roi(
    bid_price: int,
    sale_price: PriceRange,
    cost: int,
    holding_months: int = 12,
) -> tuple[float, float, float, float]:
    """수익률(ROI)을 산출한다.

    Returns:
        (roi_conservative, roi_moderate, roi_optimistic, annual_roi)
    """
    total_investment = bid_price + cost
    if total_investment <= 0:
        return 0.0, 0.0, 0.0, 0.0

    roi_con = (sale_price.conservative - total_investment) / total_investment * 100
    roi_mod = (sale_price.moderate - total_investment) / total_investment * 100
    roi_opt = (sale_price.aggressive - total_investment) / total_investment * 100

    holding_years = holding_months / 12
    annual_roi = roi_mod / holding_years if holding_years > 0 else 0.0

    return round(roi_con, 1), round(roi_mod, 1), round(roi_opt, 1), round(annual_roi, 1)


# ---------------------------------------------------------------------------
# 6. 입찰 추천 판단
# ---------------------------------------------------------------------------


def determine_recommendation(
    risk_level: str,
    roi_moderate: float,
    has_assumed_risk: bool,
) -> tuple[Recommendation, str]:
    """입찰 추천/보류/비추천을 판단한다.

    - 추천: 위험도 low + ROI >= 15%
    - 보류: 위험도 medium 또는 ROI 5~15%
    - 비추천: 위험도 high 또는 ROI < 5% 또는 인수 위험
    """
    if risk_level == "high" or roi_moderate < 5 or has_assumed_risk:
        return Recommendation.NOT_RECOMMEND, "위험도가 높거나 수익률이 낮습니다."
    elif risk_level == "low" and roi_moderate >= 15:
        return Recommendation.RECOMMEND, f"위험도 낮고 예상 수익률 {roi_moderate:.1f}%로 양호합니다."
    else:
        return Recommendation.HOLD, "추가 검토가 필요합니다."


# ---------------------------------------------------------------------------
# 7. 에이전트 노드
# ---------------------------------------------------------------------------


async def valuation_node(state: AgentState) -> AgentState:
    """가치평가 에이전트 노드.

    처리 흐름:
    1. 권리분석, 시장데이터, 뉴스분석 결과 수집
    2. 비용 산출 (취득세, 명도비 등)
    3. 입찰 적정가 산출 (3단계)
    4. 매도 적정가 산출 (3단계)
    5. 수익률 분석
    6. 입찰 추천 판단
    7. ValuationResult 생성하여 state에 저장
    """
    errors: list[str] = list(state.errors)
    rights = state.rights_analysis
    market = state.market_data
    news = state.news_analysis
    appraisal = state.appraisal
    registry = state.registry

    try:
        # 추정 시세 결정 (시장 데이터 → 감정가 → 0 순서로 fallback)
        if market and market.avg_price_per_pyeong > 0 and registry and registry.area:
            area_pyeong = registry.area / 3.305785
            estimated_value = int(market.avg_price_per_pyeong * area_pyeong)
        elif appraisal:
            estimated_value = appraisal.appraised_value
        else:
            errors.append("가치평가: 시세 추정 불가 (시장데이터·감정가 모두 없음)")
            state.valuation = None
            state.errors = errors
            return state

        property_type = registry.property_type if registry else "주택"

        # 권리분석 데이터
        assumed_cost = rights.total_assumed_amount if rights else 0
        num_tenants = len(rights.tenants) if rights else 0
        has_opposition = any(t.has_opposition_right for t in rights.tenants) if rights else False
        risk_level = rights.risk_level.value if rights else "medium"

        # 비용 산출
        costs = calculate_cost_breakdown(
            bid_price=estimated_value,
            property_type=property_type,
            assumed_rights_cost=assumed_cost,
            num_tenants=num_tenants,
            has_opposition_tenants=has_opposition,
        )
        cost_total = total_cost(costs)

        # 입찰 적정가
        bid_range = calculate_bid_price_range(estimated_value, assumed_cost, cost_total, 0)

        # 매도 적정가
        trend = market.price_trend if market else "보합"
        has_positive = bool(news and news.positive_factors)
        has_negative = bool(news and news.negative_factors)
        sale_range = calculate_sale_price_range(estimated_value, trend, has_positive, has_negative)

        # 수익률 (적정 입찰가 기준)
        roi_con, roi_mod, roi_opt, annual_roi = calculate_roi(
            bid_range.moderate, sale_range, cost_total,
        )

        # 추천 판단
        recommendation, reason = determine_recommendation(
            risk_level, roi_mod, assumed_cost > 0,
        )

        risk_summary = ""
        if rights:
            risk_summary = f"위험도: {risk_level}"
            if rights.risk_factors:
                risk_summary += f" ({', '.join(rights.risk_factors[:3])})"

        result = ValuationResult(
            recommendation=recommendation,
            bid_price=bid_range,
            sale_price=sale_range,
            expected_roi=roi_mod,
            cost_breakdown=costs,
            risk_summary=risk_summary,
            reasoning=reason,
            confidence_score=0.8,
        )

        logger.info(
            "가치평가 완료: 추천=%s, ROI=%.1f%%, 입찰적정가=%s원",
            recommendation.value,
            roi_mod,
            f"{bid_range.moderate:,}",
        )

        state.valuation = result

    except Exception as exc:
        logger.exception("가치평가 오류")
        errors.append(f"가치평가 오류: {exc}")
        state.valuation = None

    state.errors = errors
    return state
