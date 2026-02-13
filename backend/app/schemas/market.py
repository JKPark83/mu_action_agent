"""시세 데이터 스키마"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Transaction:
    """매매 실거래 내역"""

    address: str
    area: float
    price: int
    price_per_pyeong: int
    transaction_date: str


@dataclass(frozen=True)
class RentTransaction:
    """전월세 거래 내역"""

    address: str
    area: float
    deposit: int  # 보증금 (원 단위)
    monthly_rent: int  # 월세 (원 단위, 전세일 경우 0)
    transaction_date: str
    contract_type: str = ""  # 계약구분 (신규/갱신)


@dataclass(frozen=True)
class MarketDataResult:
    """시세 분석 결과"""

    recent_transactions: list[Transaction] = field(default_factory=list)
    recent_rent_transactions: list[RentTransaction] = field(default_factory=list)
    avg_price_per_pyeong: int = 0
    price_range_low: int = 0
    price_range_high: int = 0
    price_trend: str = ""  # 상승/보합/하락
    jeonse_ratio: float = 0.0
    avg_jeonse_deposit: int = 0
    avg_monthly_rent: int = 0
    appraisal_vs_market_gap: float = 0.0
    confidence_score: float = 0.0
