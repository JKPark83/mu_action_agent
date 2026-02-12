"""뉴스/시장동향 분석 스키마"""

from dataclasses import dataclass, field
from enum import Enum


class Sentiment(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


@dataclass(frozen=True)
class NewsItem:
    """뉴스 항목"""

    title: str
    source: str
    published_date: str
    sentiment: Sentiment
    summary: str
    impact_score: float = 0.0


@dataclass(frozen=True)
class NewsAnalysisResult:
    """뉴스 분석 결과"""

    collected_news: list[NewsItem] = field(default_factory=list)
    positive_factors: list[str] = field(default_factory=list)
    negative_factors: list[str] = field(default_factory=list)
    market_trend_summary: str = ""
    area_attractiveness_score: float = 0.0
    investment_opinion: str = ""
    outlook_6month: str = ""
