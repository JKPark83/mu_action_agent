"""권리분석 결과 스키마"""

from dataclasses import dataclass, field
from enum import Enum


class RiskLevel(str, Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True)
class TenantAnalysis:
    """임차인 분석"""

    name: str
    deposit: int
    has_opposition_right: bool  # 대항력
    has_priority_repayment: bool  # 우선변제권
    expected_dividend: int | None = None


@dataclass(frozen=True)
class RightsAnalysisResult:
    """권리분석 결과"""

    extinguishment_basis: str  # 말소기준권리
    assumed_rights: list[str] = field(default_factory=list)
    extinguished_rights: list[str] = field(default_factory=list)
    tenants: list[TenantAnalysis] = field(default_factory=list)
    risk_level: RiskLevel = RiskLevel.MEDIUM
    risk_factors: list[str] = field(default_factory=list)
    total_assumed_amount: int = 0
    confidence_score: float = 0.0
