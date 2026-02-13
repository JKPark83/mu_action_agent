"""뉴스/시장동향 분석 에이전트 노드"""

from __future__ import annotations

import logging

from anthropic import AsyncAnthropic

from app.agents.prompts.news_prompts import NEWS_ANALYSIS_PROMPT
from app.agents.state import AgentState
from app.agents.tools.news_api import (
    deduplicate_news,
    generate_search_queries,
    search_news,
    _strip_html,
)
from app.config import settings
from app.schemas.news import NewsAnalysisResult, NewsItem, Sentiment

logger = logging.getLogger(__name__)

_client: AsyncAnthropic | None = None


def _get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        _client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


# ---------------------------------------------------------------------------
# tool_use 스키마 — Claude가 항상 유효한 JSON 구조로 응답하도록 강제
# ---------------------------------------------------------------------------

NEWS_ANALYSIS_TOOL = {
    "name": "save_news_analysis",
    "description": "뉴스 분석 결과를 저장합니다.",
    "input_schema": {
        "type": "object",
        "properties": {
            "analyzed_news": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "sentiment": {
                            "type": "string",
                            "enum": ["positive", "negative", "neutral"],
                        },
                        "impact_score": {"type": "number"},
                        "summary": {"type": "string"},
                    },
                    "required": ["title", "sentiment", "impact_score", "summary"],
                },
            },
            "positive_factors": {"type": "array", "items": {"type": "string"}},
            "negative_factors": {"type": "array", "items": {"type": "string"}},
            "area_attractiveness_score": {"type": "number"},
            "investment_opinion": {"type": "string"},
            "outlook": {"type": "string", "enum": ["긍정", "중립", "부정"]},
            "market_trend_summary": {"type": "string"},
        },
        "required": [
            "analyzed_news",
            "positive_factors",
            "negative_factors",
            "area_attractiveness_score",
            "investment_opinion",
            "outlook",
            "market_trend_summary",
        ],
    },
}


async def _call_llm_structured(prompt: str, max_tokens: int = 8192) -> dict:
    """Anthropic Claude API를 tool_use 방식으로 호출하여 구조화된 dict를 반환한다."""
    client = _get_client()
    response = await client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
        tools=[NEWS_ANALYSIS_TOOL],
        tool_choice={"type": "tool", "name": "save_news_analysis"},
    )
    for block in response.content:
        if block.type == "tool_use":
            return block.input
    raise ValueError("LLM이 tool_use 응답을 반환하지 않았습니다.")


# ---------------------------------------------------------------------------
# Claude 뉴스 분석
# ---------------------------------------------------------------------------


def _format_news_for_prompt(items: list[dict]) -> str:
    """뉴스 아이템을 LLM 프롬프트 입력 문자열로 변환한다."""
    lines: list[str] = []
    for i, item in enumerate(items, 1):
        title = _strip_html(item.get("title", ""))
        desc = _strip_html(item.get("description", ""))
        pub_date = item.get("pubDate", "")
        lines.append(f"{i}. 제목: {title}\n   내용: {desc}\n   날짜: {pub_date}")
    return "\n".join(lines)


def _parse_sentiment(value: str) -> Sentiment:
    """문자열을 Sentiment enum으로 변환한다."""
    mapping = {
        "positive": Sentiment.POSITIVE,
        "negative": Sentiment.NEGATIVE,
        "neutral": Sentiment.NEUTRAL,
        "호재": Sentiment.POSITIVE,
        "악재": Sentiment.NEGATIVE,
        "중립": Sentiment.NEUTRAL,
    }
    return mapping.get(value.lower(), Sentiment.NEUTRAL)


async def analyze_news_with_claude(
    news_items: list[dict],
    target_area: str,
) -> dict:
    """Claude를 활용하여 뉴스를 분류/요약/종합 분석한다."""
    news_text = _format_news_for_prompt(news_items)
    prompt = NEWS_ANALYSIS_PROMPT.format(area=target_area, news_list=news_text)

    return await _call_llm_structured(prompt)


# ---------------------------------------------------------------------------
# 에이전트 노드
# ---------------------------------------------------------------------------


async def news_analysis_node(state: AgentState) -> dict:
    """뉴스 분석 에이전트 노드.

    처리 흐름:
    1. state에서 소재지 정보 가져오기
    2. 검색 키워드 자동 생성
    3. 키워드별 네이버 뉴스 API 호출
    4. 중복 뉴스 제거
    5. Claude로 뉴스 분류/요약/종합 분석
    6. NewsAnalysisResult를 partial dict로 반환
    """
    new_errors: list[str] = []
    registry = state.get("registry")

    if not registry:
        new_errors.append("뉴스분석 실패: 소재지 정보 없음")
        result_dict: dict = {"news_analysis": None}
        if new_errors:
            result_dict["errors"] = new_errors
        return result_dict

    try:
        address = registry.property_address
        building_name = getattr(registry, "building_name", None) or ""
        queries = generate_search_queries(address, apt_name=building_name)
        logger.info("뉴스분석 시작: %s (키워드 %d개: %s)", address, len(queries), queries)

        # 뉴스 수집
        all_news: list[dict] = []
        failed_queries: list[str] = []
        for query in queries:
            try:
                items = await search_news(query, display=10)
                if not items:
                    logger.warning("뉴스 검색 결과 0건: 키워드='%s'", query)
                all_news.extend(items)
            except Exception as exc:
                failed_queries.append(query)
                logger.warning("뉴스 검색 실패 (%s): %s", query, exc)
                continue

        if failed_queries:
            logger.error(
                "뉴스 API 호출 실패 %d/%d 키워드: %s",
                len(failed_queries), len(queries), failed_queries,
            )

        # 중복 제거
        unique_news = deduplicate_news(all_news)
        logger.info("뉴스 수집 완료: %d건 (중복 제거 후 %d건)", len(all_news), len(unique_news))

        if not unique_news:
            logger.error(
                "뉴스분석 실패: 수집된 뉴스 0건. 키워드: %s, API 실패: %d건, 주소: %s",
                queries, len(failed_queries), address,
            )
            new_errors.append(
                f"뉴스분석: 수집된 뉴스 없음 ({address}). "
                f"키워드 {len(queries)}개 모두 결과 없음. 네이버 API 키를 확인하세요."
            )
            result_dict = {"news_analysis": None}
            if new_errors:
                result_dict["errors"] = new_errors
            return result_dict

        # Claude 분석 (최대 15건 — 토큰 초과 방지)
        analysis = await analyze_news_with_claude(unique_news[:15], address)

        # 개별 뉴스 → NewsItem 변환
        collected: list[NewsItem] = []
        for item in analysis.get("analyzed_news", []):
            collected.append(
                NewsItem(
                    title=item.get("title", ""),
                    source="",
                    published_date="",
                    sentiment=_parse_sentiment(item.get("sentiment", "neutral")),
                    summary=item.get("summary", ""),
                    impact_score=float(item.get("impact_score", 0)),
                )
            )

        result = NewsAnalysisResult(
            collected_news=collected,
            positive_factors=analysis.get("positive_factors", []),
            negative_factors=analysis.get("negative_factors", []),
            market_trend_summary=analysis.get("market_trend_summary", ""),
            area_attractiveness_score=float(analysis.get("area_attractiveness_score", 0)),
            investment_opinion=analysis.get("investment_opinion", ""),
            outlook_6month=analysis.get("outlook", "중립"),
        )

        logger.info(
            "뉴스분석 완료: 뉴스 %d건, 호재 %d건, 악재 %d건, 매력도 %.0f",
            len(collected),
            len(result.positive_factors),
            len(result.negative_factors),
            result.area_attractiveness_score,
        )

        result_dict = {"news_analysis": result}

    except Exception as exc:
        logger.exception("뉴스분석 오류")
        new_errors.append(f"뉴스분석 오류: {exc}")
        result_dict = {"news_analysis": None}

    if new_errors:
        result_dict["errors"] = new_errors
    return result_dict
