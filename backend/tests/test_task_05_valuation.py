"""Task-05: 가치 평가 엔진 단위 테스트

모든 함수가 순수 Python 로직이므로 외부 의존성 없이 테스트한다.
"""

from __future__ import annotations

import pytest

from app.agents.nodes.valuation import (
    calculate_acquisition_tax,
    calculate_bid_price_range,
    calculate_cost_breakdown,
    calculate_roi,
    calculate_sale_price_range,
    determine_recommendation,
    total_cost,
    valuation_node,
)
from app.agents.state import AgentState
from app.schemas.document import AppraisalExtraction, RegistryExtraction
from app.schemas.valuation import PriceRange, Recommendation


# ---------------------------------------------------------------------------
# T-1: 6억 이하 취득세 (1%)
# ---------------------------------------------------------------------------


def test_acquisition_tax_under_600m():
    """6억 이하 1주택 취득세는 1%."""
    tax = calculate_acquisition_tax(500_000_000, "아파트")
    assert tax == 5_000_000  # 5억 × 1%


# ---------------------------------------------------------------------------
# T-2: 9억 초과 취득세 (3%)
# ---------------------------------------------------------------------------


def test_acquisition_tax_over_900m():
    """9억 초과 1주택 취득세는 3%."""
    tax = calculate_acquisition_tax(1_000_000_000, "아파트")
    assert tax == 30_000_000  # 10억 × 3%


def test_acquisition_tax_commercial():
    """상가 취득세는 4.6%."""
    tax = calculate_acquisition_tax(500_000_000, "상가")
    assert tax == 23_000_000  # 5억 × 4.6%


# ---------------------------------------------------------------------------
# T-3: 입찰 적정가 3단계 순서
# ---------------------------------------------------------------------------


def test_bid_price_range():
    """보수적 < 적정 < 공격적 순서."""
    bid = calculate_bid_price_range(
        estimated_market_value=1_000_000_000,
        assumed_rights_cost=0,
        extra_cost=0,
        minimum_bid=0,
    )

    assert bid.conservative < bid.moderate < bid.aggressive
    assert bid.conservative == 650_000_000  # 10억 × 0.65
    assert bid.moderate == 750_000_000  # 10억 × 0.75
    assert bid.aggressive == 850_000_000  # 10억 × 0.85


def test_bid_price_with_deductions():
    """인수비용과 부대비용이 차감된다."""
    bid = calculate_bid_price_range(
        estimated_market_value=1_000_000_000,
        assumed_rights_cost=50_000_000,
        extra_cost=20_000_000,
        minimum_bid=0,
    )

    # 10억 × 0.75 - 5000만 - 2000만 = 6.8억
    assert bid.moderate == 680_000_000


# ---------------------------------------------------------------------------
# T-4: 양의 수익률
# ---------------------------------------------------------------------------


def test_roi_positive():
    """매도가 > 총투자비용이면 양의 ROI."""
    sale = PriceRange(
        conservative=900_000_000,
        moderate=1_000_000_000,
        aggressive=1_100_000_000,
    )

    roi_con, roi_mod, roi_opt, annual = calculate_roi(
        bid_price=700_000_000,
        sale_price=sale,
        cost=50_000_000,
    )

    # 총투자 = 7억 + 5천만 = 7.5억
    # roi_mod = (10억 - 7.5억) / 7.5억 × 100 = 33.3%
    assert roi_mod > 0
    assert roi_con < roi_mod < roi_opt
    assert annual > 0


# ---------------------------------------------------------------------------
# T-5: 고수익+저위험 → 추천 (인수위험 없을 때)
# ---------------------------------------------------------------------------


def test_recommend_high_roi_low_risk():
    """위험도 low + ROI >= 15% + 인수 위험 없음 → 추천."""
    rec, reason = determine_recommendation(
        risk_level="low",
        roi_moderate=20.0,
        has_assumed_risk=False,
    )

    assert rec == Recommendation.RECOMMEND
    assert "20.0%" in reason


# ---------------------------------------------------------------------------
# T-6: 고위험 → 비추천
# ---------------------------------------------------------------------------


def test_not_recommend_high_risk():
    """위험도 high → 비추천."""
    rec, reason = determine_recommendation(
        risk_level="high",
        roi_moderate=30.0,
        has_assumed_risk=False,
    )

    assert rec == Recommendation.NOT_RECOMMEND


def test_not_recommend_low_roi():
    """ROI < 5% → 비추천."""
    rec, reason = determine_recommendation(
        risk_level="low",
        roi_moderate=3.0,
        has_assumed_risk=False,
    )

    assert rec == Recommendation.NOT_RECOMMEND


def test_hold_medium_risk():
    """위험도 medium + ROI 적정 → 보류."""
    rec, reason = determine_recommendation(
        risk_level="medium",
        roi_moderate=10.0,
        has_assumed_risk=False,
    )

    assert rec == Recommendation.HOLD


# ---------------------------------------------------------------------------
# T-7: 비용 합계
# ---------------------------------------------------------------------------


def test_cost_breakdown_sum():
    """total_cost는 모든 비용 항목의 합이다."""
    costs = calculate_cost_breakdown(
        bid_price=500_000_000,
        property_type="아파트",
        assumed_rights_cost=0,
        num_tenants=1,
        has_opposition_tenants=False,
    )

    expected = (
        costs.acquisition_tax
        + costs.registration_fee
        + costs.legal_fee
        + costs.eviction_cost
        + costs.repair_cost
        + costs.capital_gains_tax
    )

    assert total_cost(costs) == expected
    assert total_cost(costs) > 0


# ---------------------------------------------------------------------------
# T-8: 노드 — 시세 추정 불가 시 에러
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_valuation_node_no_data():
    """시장데이터·감정가 모두 없으면 에러."""
    state = AgentState(analysis_id="test-no-val")

    result = await valuation_node(state)

    assert result.valuation is None
    assert any("시세 추정 불가" in e for e in result.errors)


# ---------------------------------------------------------------------------
# T-9: 노드 — 감정가 fallback
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_valuation_node_appraisal_fallback():
    """시장데이터 없이 감정가만으로도 평가를 수행한다."""
    state = AgentState(
        analysis_id="test-appraisal",
        appraisal=AppraisalExtraction(appraised_value=500_000_000),
    )

    result = await valuation_node(state)

    assert result.valuation is not None
    assert result.valuation.bid_price.conservative > 0
    assert result.valuation.bid_price.moderate > result.valuation.bid_price.conservative
