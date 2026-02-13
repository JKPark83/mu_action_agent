"""네이버 뉴스 검색 API 클라이언트"""

from __future__ import annotations

import logging
import re

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

NAVER_SEARCH_URL = "https://openapi.naver.com/v1/search/news.json"


def generate_search_queries(address: str, apt_name: str = "") -> list[str]:
    """소재지 주소에서 뉴스 검색 키워드를 자동 생성한다.

    Args:
        address: 소재지 주소
        apt_name: 아파트/단지명 (있으면 추가 키워드 생성)

    Examples:
        >>> generate_search_queries("경기도 김포시 운양동 1301-1 한강신도시롯데캐슬 301동")
        ['김포시 부동산 시장', '김포시 부동산 전망', '김포시 개발 호재', '운양동 부동산', '운양동 개발', '한강신도시롯데캐슬']
    """
    parts = address.split()
    gu = next((p for p in parts if p.endswith("구")), "")
    dong = next((p for p in parts if p.endswith("동") and not p[-2:].isdigit()), "")
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
    # 구가 없는 시 단위 주소 (김포시, 평택시 등)
    if si:
        if not gu:
            queries.extend([
                f"{si} 부동산 시장",
                f"{si} 부동산 전망",
                f"{si} 개발 호재",
            ])
        else:
            queries.append(f"{si} 부동산 전망")

    # 아파트/단지명이 주소에 포함된 경우 추출하여 검색
    if not apt_name:
        # 주소에서 아파트 단지명 추출 시도 (한글+숫자 조합, 일반적으로 동 번호 앞에 위치)
        for part in parts:
            if len(part) >= 4 and not part.endswith(("시", "구", "동", "로", "길")) and not part[0].isdigit():
                apt_name = part
                break
    if apt_name:
        queries.append(f"{apt_name} 시세")

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
