"""LangGraph 에이전트 상태 정의"""

from dataclasses import dataclass, field

from app.schemas.document import RegistryExtraction, AppraisalExtraction, SaleItemExtraction
from app.schemas.market import MarketDataResult
from app.schemas.news import NewsAnalysisResult
from app.schemas.rights import RightsAnalysisResult
from app.schemas.valuation import ValuationResult


@dataclass
class AgentState:
    """LangGraph 워크플로우 전체 상태"""

    # 입력
    analysis_id: str = ""
    file_paths: list[str] = field(default_factory=list)

    # 문서 파싱 결과
    registry: RegistryExtraction | None = None
    appraisal: AppraisalExtraction | None = None
    sale_item: SaleItemExtraction | None = None

    # 분석 결과
    rights_analysis: RightsAnalysisResult | None = None
    market_data: MarketDataResult | None = None
    news_analysis: NewsAnalysisResult | None = None
    valuation: ValuationResult | None = None

    # 최종 보고서
    report: dict | None = None

    # 에러 추적
    errors: list[str] = field(default_factory=list)
