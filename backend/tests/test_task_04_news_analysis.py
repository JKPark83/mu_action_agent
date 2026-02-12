"""Task-04: 뉴스 분석 에이전트 단위 테스트

외부 API(네이버, Claude) 호출은 모두 mock 처리하여 외부 의존성 없이 테스트한다.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.agents.nodes.news_analysis import (
    _parse_sentiment,
    news_analysis_node,
)
from app.agents.state import AgentState
from app.agents.tools.news_api import (
    deduplicate_news,
    generate_search_queries,
)
from app.schemas.document import RegistryExtraction
from app.schemas.news import Sentiment


# ---------------------------------------------------------------------------
# T-1: 키워드 자동 생성
# ---------------------------------------------------------------------------


def test_generate_queries():
    """주소에서 5개 이상의 검색 키워드를 생성한다."""
    queries = generate_search_queries("서울특별시 강남구 역삼동 123-45")

    assert len(queries) >= 5
    # 구 단위 키워드 포함
    assert any("강남구" in q for q in queries)
    # 동 단위 키워드 포함
    assert any("역삼동" in q for q in queries)
    # 부동산 관련 키워드 포함
    assert any("부동산" in q for q in queries)


def test_generate_queries_no_gu():
    """구가 없고 시만 있는 주소에서도 키워드를 생성한다."""
    queries = generate_search_queries("경기도 평택시 123")

    assert len(queries) >= 2
    assert any("평택시" in q for q in queries)


# ---------------------------------------------------------------------------
# T-2: 중복 뉴스 제거
# ---------------------------------------------------------------------------


def test_dedup_news():
    """제목 기준으로 중복 뉴스를 제거한다."""
    items = [
        {"title": "강남구 <b>재개발</b> 호재", "description": "내용1"},
        {"title": "강남구 <b>재개발</b> 호재", "description": "내용2"},  # 중복
        {"title": "역삼동 교통 개선", "description": "내용3"},
    ]

    unique = deduplicate_news(items)

    assert len(unique) == 2
    # HTML 태그 제거 후 비교
    titles = [item["title"] for item in unique]
    assert "강남구 <b>재개발</b> 호재" in titles
    assert "역삼동 교통 개선" in titles


# ---------------------------------------------------------------------------
# T-3: Sentiment 파싱
# ---------------------------------------------------------------------------


def test_parse_sentiment():
    """다양한 sentiment 문자열을 올바르게 변환한다."""
    assert _parse_sentiment("positive") == Sentiment.POSITIVE
    assert _parse_sentiment("negative") == Sentiment.NEGATIVE
    assert _parse_sentiment("neutral") == Sentiment.NEUTRAL
    assert _parse_sentiment("호재") == Sentiment.POSITIVE
    assert _parse_sentiment("악재") == Sentiment.NEGATIVE
    assert _parse_sentiment("unknown") == Sentiment.NEUTRAL


# ---------------------------------------------------------------------------
# T-4: Claude 뉴스 분석 (mock)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_analyze_news_with_claude():
    """Claude 분석 결과를 올바르게 파싱하여 NewsAnalysisResult를 생성한다."""
    mock_claude_response = json.dumps({
        "analyzed_news": [
            {
                "title": "강남구 재개발 사업 승인",
                "sentiment": "positive",
                "impact_score": 8,
                "summary": "강남구 역삼동 일대 재개발 사업이 최종 승인됨",
            },
            {
                "title": "금리 인상 우려",
                "sentiment": "negative",
                "impact_score": 6,
                "summary": "한은 기준금리 인상 가능성에 부동산 시장 위축 전망",
            },
        ],
        "positive_factors": ["재개발 사업 승인", "교통 인프라 개선"],
        "negative_factors": ["금리 인상 우려"],
        "area_attractiveness_score": 75,
        "investment_opinion": "강남구 역삼동은 재개발 호재가 있으나 금리 부담이 있습니다.",
        "outlook": "긍정",
        "market_trend_summary": "개발 호재로 인해 상승세가 예상됩니다.",
    })

    mock_registry = RegistryExtraction(
        property_address="서울특별시 강남구 역삼동 123-45",
        property_type="아파트",
    )

    state = AgentState(analysis_id="test-news", registry=mock_registry)

    # search_news를 mock하여 뉴스 반환
    mock_news = [
        {"title": "강남구 재개발 사업 승인", "description": "내용1", "pubDate": "2025-01-01"},
        {"title": "금리 인상 우려", "description": "내용2", "pubDate": "2025-01-02"},
    ]

    with (
        patch(
            "app.agents.nodes.news_analysis.search_news",
            new_callable=AsyncMock,
            return_value=mock_news,
        ),
        patch(
            "app.agents.nodes.news_analysis._call_llm",
            new_callable=AsyncMock,
            return_value=mock_claude_response,
        ),
    ):
        result = await news_analysis_node(state)

    assert result.news_analysis is not None
    assert len(result.news_analysis.collected_news) == 2
    assert result.news_analysis.collected_news[0].sentiment == Sentiment.POSITIVE
    assert result.news_analysis.collected_news[1].sentiment == Sentiment.NEGATIVE
    assert len(result.news_analysis.positive_factors) == 2
    assert len(result.news_analysis.negative_factors) == 1
    assert result.news_analysis.area_attractiveness_score == 75
    assert result.news_analysis.outlook_6month == "긍정"
    assert len(result.errors) == 0


# ---------------------------------------------------------------------------
# T-5: registry 없으면 에러
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_news_node_no_address():
    """registry가 없으면 에러 메시지를 추가한다."""
    state = AgentState(analysis_id="test-no-addr")

    result = await news_analysis_node(state)

    assert result.news_analysis is None
    assert len(result.errors) == 1
    assert "소재지" in result.errors[0]
