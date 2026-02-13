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
    move_in_date: str | None = None  # 전입일
    confirmed_date: str | None = None  # 확정일자
    dividend_applied: bool = False  # 배당신청 여부
    dividend_ranking: int | None = None  # 배당순위 (0=최우선변제, 1~N=일반순위, None=배당불가)
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
    total_assumed_amount: int = 0  # 인수할 권리 총액 (선순위 권리)
    total_assumed_deposit: int = 0  # 대항력 있는 임차인 보증금 합계
    confidence_score: float = 0.0
