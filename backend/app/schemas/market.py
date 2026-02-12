"""시세 데이터 스키마"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Transaction:
    """실거래 내역"""

    address: str
    area: float
    price: int
    price_per_pyeong: int
    transaction_date: str


@dataclass(frozen=True)
class MarketDataResult:
    """시세 분석 결과"""

    recent_transactions: list[Transaction] = field(default_factory=list)
    avg_price_per_pyeong: int = 0
    price_range_low: int = 0
    price_range_high: int = 0
    price_trend: str = ""  # 상승/보합/하락
    jeonse_ratio: float = 0.0
    appraisal_vs_market_gap: float = 0.0
    confidence_score: float = 0.0
