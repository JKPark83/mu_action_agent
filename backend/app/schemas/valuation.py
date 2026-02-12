"""가치평가 및 입찰 추천 스키마"""

from dataclasses import dataclass, field
from enum import Enum


class Recommendation(str, Enum):
    RECOMMEND = "recommend"  # 추천
    HOLD = "hold"  # 보류
    NOT_RECOMMEND = "not_recommend"  # 비추천


@dataclass(frozen=True)
class PriceRange:
    """가격 범위 (보수적/적정/공격적 또는 비관/기본/낙관)"""

    conservative: int = 0
    moderate: int = 0
    aggressive: int = 0


@dataclass(frozen=True)
class CostBreakdown:
    """비용 내역"""

    acquisition_tax: int = 0
    registration_fee: int = 0
    legal_fee: int = 0
    eviction_cost: int = 0
    repair_cost: int = 0
    capital_gains_tax: int = 0


@dataclass(frozen=True)
class ValuationResult:
    """최종 가치평가 결과"""

    recommendation: Recommendation = Recommendation.HOLD
    bid_price: PriceRange = field(default_factory=PriceRange)
    sale_price: PriceRange = field(default_factory=PriceRange)
    expected_roi: float = 0.0
    cost_breakdown: CostBreakdown = field(default_factory=CostBreakdown)
    risk_summary: str = ""
    reasoning: str = ""
    confidence_score: float = 0.0
