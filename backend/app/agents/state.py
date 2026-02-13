"""LangGraph 에이전트 상태 정의"""

import operator
from typing import Annotated, TypedDict

from app.schemas.document import AppraisalExtraction, RegistryExtraction, SaleItemExtraction, StatusReportExtraction
from app.schemas.market import MarketDataResult
from app.schemas.news import NewsAnalysisResult
from app.schemas.rights import RightsAnalysisResult
from app.schemas.valuation import ValuationResult


class AgentState(TypedDict, total=False):
    """LangGraph 워크플로우 전체 상태"""

    # 입력
    analysis_id: str
    file_paths: list[str]

    # 문서 파싱 결과
    registry: RegistryExtraction | None
    appraisal: AppraisalExtraction | None
    sale_item: SaleItemExtraction | None
    status_report: StatusReportExtraction | None

    # 분석 결과
    rights_analysis: RightsAnalysisResult | None
    market_data: MarketDataResult | None
    news_analysis: NewsAnalysisResult | None
    valuation: ValuationResult | None

    # 최종 보고서
    report: dict | None

    # 에러 추적 (reducer: 새 에러를 기존 에러에 concatenate)
    errors: Annotated[list[str], operator.add]
