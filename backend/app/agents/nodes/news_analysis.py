"""뉴스/시장동향 분석 에이전트 노드"""

from __future__ import annotations

import json
import logging
import re

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


def _parse_json_response(text: str) -> dict:
    """LLM 응답에서 JSON을 추출한다."""
    # 1. ```json ... ``` 블록
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        return json.loads(match.group(1).strip())
    # 2. 텍스트 내 첫 번째 { ... } 블록
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        return json.loads(match.group(0))
    # 3. 전체가 JSON
    return json.loads(text.strip())


async def _call_llm(prompt: str, max_tokens: int = 4096) -> str:
    """Anthropic Claude API를 호출한다."""
    client = _get_client()
    response = await client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


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

    raw = await _call_llm(prompt)
    return _parse_json_response(raw)


# ---------------------------------------------------------------------------
# 에이전트 노드
# ---------------------------------------------------------------------------


async def news_analysis_node(state: AgentState) -> AgentState:
    """뉴스 분석 에이전트 노드.

    처리 흐름:
    1. state에서 소재지 정보 가져오기
    2. 검색 키워드 자동 생성
    3. 키워드별 네이버 뉴스 API 호출
    4. 중복 뉴스 제거
    5. Claude로 뉴스 분류/요약/종합 분석
    6. NewsAnalysisResult 생성하여 state에 저장
    """
    errors: list[str] = list(state.errors)
    registry = state.registry

    if not registry:
        errors.append("뉴스분석 실패: 소재지 정보 없음")
        state.news_analysis = None
        state.errors = errors
        return state

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
            errors.append(
                f"뉴스분석: 수집된 뉴스 없음 ({address}). "
                f"키워드 {len(queries)}개 모두 결과 없음. 네이버 API 키를 확인하세요."
            )
            state.news_analysis = None
            state.errors = errors
            return state

        # Claude 분석 (최대 30건)
        analysis = await analyze_news_with_claude(unique_news[:30], address)

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

        state.news_analysis = result

    except Exception as exc:
        logger.exception("뉴스분석 오류")
        errors.append(f"뉴스분석 오류: {exc}")
        state.news_analysis = None

    state.errors = errors
    return state
