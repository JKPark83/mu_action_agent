"""네이버 뉴스 검색 API 클라이언트"""

from __future__ import annotations

import logging
import re

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

NAVER_SEARCH_URL = "https://openapi.naver.com/v1/search/news.json"


def generate_search_queries(address: str) -> list[str]:
    """소재지 주소에서 뉴스 검색 키워드를 자동 생성한다.

    Examples:
        >>> generate_search_queries("서울특별시 강남구 역삼동 123-45")
        ['강남구 부동산 시장', '강남구 재개발 재건축', '강남구 개발 호재', '강남구 부동산 전망', '역삼동 부동산', '역삼동 개발']
    """
    parts = address.split()
    gu = next((p for p in parts if p.endswith("구")), "")
    dong = next((p for p in parts if p.endswith("동")), "")
    si = next((p for p in parts if p.endswith("시")), "")

    queries: list[str] = []

    if gu:
        queries.extend([
            f"{gu} 부동산 시장",
            f"{gu} 재개발 재건축",
            f"{gu} 개발 호재",
            f"{gu} 부동산 전망",
        ])
    if dong:
        queries.extend([
            f"{dong} 부동산",
            f"{dong} 개발",
        ])
    if not gu and si:
        queries.extend([
            f"{si} 부동산 시장",
            f"{si} 재개발",
            f"{si} 부동산 전망",
        ])

    return queries


def _strip_html(text: str) -> str:
    """HTML 태그를 제거한다."""
    return re.sub(r"<[^>]+>", "", text)


def deduplicate_news(items: list[dict]) -> list[dict]:
    """제목 기준으로 중복 뉴스를 제거한다."""
    seen: set[str] = set()
    unique: list[dict] = []
    for item in items:
        title = _strip_html(item.get("title", ""))
        if title and title not in seen:
            seen.add(title)
            unique.append(item)
    return unique


async def search_news(
    query: str,
    display: int = 20,
    sort: str = "date",
) -> list[dict]:
    """네이버 뉴스 검색 API를 호출한다.

    Args:
        query: 검색 키워드
        display: 검색 결과 수 (최대 100)
        sort: 정렬 방식 (date: 날짜순, sim: 관련도순)

    Returns:
        뉴스 항목 dict 리스트 (title, description, link, pubDate 등)
    """
    headers = {
        "X-Naver-Client-Id": settings.naver_client_id,
        "X-Naver-Client-Secret": settings.naver_client_secret,
    }
    params = {
        "query": query,
        "display": display,
        "sort": sort,
    }

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(NAVER_SEARCH_URL, headers=headers, params=params)
        response.raise_for_status()

    data = response.json()
    return data.get("items", [])
