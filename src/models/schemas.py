from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class PropertyType(str, Enum):
    APARTMENT = "아파트"
    VILLA = "연립다세대"
    HOUSE = "단독다가구"
    OFFICETEL = "오피스텔"
    COMMERCIAL = "상가"
    LAND = "토지"


class RiskGrade(str, Enum):
    A = "A"  # 안전
    B = "B"  # 주의
    C = "C"  # 위험
    D = "D"  # 고위험


class RightType(str, Enum):
    MORTGAGE = "근저당권"
    SEIZURE = "압류"
    PROVISIONAL_SEIZURE = "가압류"
    SECURITY_DEPOSIT = "전세권"
    TENANT = "임차인"
    LIEN = "유치권"
    SUPERFICIES = "법정지상권"
    PROVISIONAL_REGISTRATION = "가등기"
    OTHER = "기타"


# --- 입력 모델 ---


class RightEntry(BaseModel):
    type: RightType
    creditor: str = Field(description="권리자/채권자명")
    amount: int = Field(ge=0, description="채권액 또는 보증금 (원)")
    date: str = Field(description="설정일 또는 전입일 (YYYY-MM-DD)")
    is_senior: bool = Field(default=False, description="말소기준권리 대비 선순위 여부")
    note: str = Field(default="", description="비고")


class AuctionCaseInput(BaseModel):
    case_number: str | None = Field(default=None, description="사건번호")
    court: str | None = Field(default=None, description="관할법원")
    property_type: PropertyType = Field(description="물건종류")
    address: str = Field(description="소재지 전체 주소")
    area_m2: float | None = Field(default=None, ge=0, description="전용면적 (m2)")
    appraisal_value: int = Field(gt=0, description="감정가 (원)")
    minimum_bid: int = Field(gt=0, description="최저매각가격 (원)")
    bid_count: int = Field(default=0, ge=0, description="유찰 횟수")
    rights: list[RightEntry] = Field(default_factory=list, description="권리관계 목록")


# --- 시세 모델 ---


class TransactionRecord(BaseModel):
    deal_date: str = Field(description="거래 연월 (YYYY-MM)")
    deal_amount: int = Field(description="거래금액 (원)")
    area_m2: float = Field(description="전용면적 (m2)")
    floor: int | None = Field(default=None, description="층")
    building_name: str | None = Field(default=None, description="건물명")


class MarketDataResponse(BaseModel):
    recent_transactions: list[TransactionRecord] = Field(default_factory=list)
    avg_price_per_m2: int = Field(default=0, description="m2당 평균 시세 (원)")
    transaction_volume: int = Field(default=0, description="조회 기간 내 거래 건수")
    price_trend: str = Field(default="데이터 없음", description="시세 추이")
    price_trend_detail: str = Field(default="", description="시세 추이 상세 설명")
    data_period: str = Field(default="", description="데이터 조회 기간")


# --- 분석 결과 모델 ---


class BidRecommendation(BaseModel):
    min_bid: int = Field(description="추천 최저 입찰가")
    max_bid: int = Field(description="추천 최고 입찰가")
    optimal_bid: int = Field(description="최적 입찰가")
    appraisal_ratio: float = Field(description="감정가 대비 비율")
    market_ratio: float = Field(description="시세 대비 비율")
    reasoning: str = Field(description="산출 근거 설명")


class CostBreakdown(BaseModel):
    acquisition_tax: int = Field(description="취득세")
    registration_fee: int = Field(description="등기비용")
    eviction_cost: int = Field(default=0, description="명도비용")
    repair_estimate: int = Field(default=5_000_000, description="수리비 추정")
    agent_fee: int = Field(default=0, description="중개수수료")
    capital_gains_tax_estimate: int = Field(default=0, description="양도세 추정")

    @property
    def total(self) -> int:
        return (
            self.acquisition_tax
            + self.registration_fee
            + self.eviction_cost
            + self.repair_estimate
            + self.agent_fee
            + self.capital_gains_tax_estimate
        )


class SalePriceEstimate(BaseModel):
    optimistic: int = Field(description="낙관적 매도가")
    realistic: int = Field(description="현실적 매도가")
    conservative: int = Field(description="보수적 매도가")
    costs: CostBreakdown
    net_profit_estimate: int = Field(description="순수익 추정 (현실적 기준)")
    roi_percent: float = Field(description="수익률 (%)")


class RightAnalysisDetail(BaseModel):
    right_type: str
    analysis: str
    risk_level: str
    assumed_amount: int = Field(description="인수해야 할 금액")


class RightsAssessment(BaseModel):
    risk_grade: RiskGrade
    risk_grade_label: str
    summary: str
    total_assumed_amount: int
    details: list[RightAnalysisDetail]
    recommendations: list[str]


# --- 종합 결과 ---


class FullAnalysisResult(BaseModel):
    auction_case: AuctionCaseInput
    market_data: MarketDataResponse | None = None
    bid_recommendation: BidRecommendation | None = None
    sale_estimate: SalePriceEstimate | None = None
    rights_assessment: RightsAssessment | None = None
    overall_opinion: str = Field(default="", description="AI 종합 의견")
    disclaimers: list[str] = Field(
        default_factory=lambda: [
            "본 서비스는 AI 기반의 참고용 분석 도구입니다.",
            "제공되는 모든 분석 결과는 투자 권유가 아니며, 투자 판단의 책임은 사용자에게 있습니다.",
            "권리분석은 법률 전문가의 검토를 대체할 수 없습니다.",
            "시세 및 수익률 추정은 실제와 다를 수 있습니다.",
            "세금 관련 사항은 세무 전문가와 상담하시기 바랍니다.",
        ]
    )
