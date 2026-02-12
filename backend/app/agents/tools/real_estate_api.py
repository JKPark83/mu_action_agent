"""국토교통부 공공데이터 API 클라이언트"""

from __future__ import annotations

import logging
import xml.etree.ElementTree as ET

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

MOLIT_BASE_URL = "http://openapi.molit.go.kr"

# 부동산 유형별 API 경로
API_ENDPOINTS: dict[str, str] = {
    "아파트매매": "/OpenAPI_ToolInstall498/service/rest/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev",
    "아파트전월세": "/OpenAPI_ToolInstall498/service/rest/RTMSDataSvcAptRent/getRTMSDataSvcAptRent",
    "연립다세대": "/OpenAPI_ToolInstall498/service/rest/RTMSDataSvcRHTradeDev/getRTMSDataSvcRHTradeDev",
    "단독다가구": "/OpenAPI_ToolInstall498/service/rest/RTMSDataSvcSHTradeDev/getRTMSDataSvcSHTradeDev",
    "오피스텔": "/OpenAPI_ToolInstall498/service/rest/RTMSDataSvcOffiTradeDev/getRTMSDataSvcOffiTradeDev",
}

# 부동산 유형 문자열 → API 키 매핑
PROPERTY_TYPE_MAP: dict[str, str] = {
    "아파트": "아파트매매",
    "연립": "연립다세대",
    "다세대": "연립다세대",
    "빌라": "연립다세대",
    "단독": "단독다가구",
    "다가구": "단독다가구",
    "오피스텔": "오피스텔",
}


def parse_xml_response(xml_text: str) -> list[dict]:
    """MOLIT API XML 응답을 dict 리스트로 변환한다.

    거래금액은 만원 단위로 제공되므로 원 단위(*10,000)로 변환한다.
    """
    root = ET.fromstring(xml_text)
    items = root.findall(".//item")

    transactions: list[dict] = []
    for item in items:
        raw_amount = (item.findtext("거래금액") or "0").strip().replace(",", "")
        try:
            amount = int(raw_amount) * 10_000  # 만원 → 원
        except ValueError:
            amount = 0

        raw_area = (item.findtext("전용면적") or "0").strip()
        try:
            area = float(raw_area)
        except ValueError:
            area = 0.0

        transactions.append({
            "거래금액": amount,
            "건축년도": (item.findtext("건축년도") or "").strip(),
            "년": (item.findtext("년") or "").strip(),
            "월": (item.findtext("월") or "").strip(),
            "일": (item.findtext("일") or "").strip(),
            "전용면적": area,
            "층": (item.findtext("층") or "").strip(),
            "아파트": (
                (item.findtext("아파트") or "").strip()
                or (item.findtext("연립다세대") or "").strip()
            ),
            "법정동": (item.findtext("법정동") or "").strip(),
        })

    return transactions


def resolve_property_type(property_type_text: str) -> str:
    """부동산 유형 문자열을 API 엔드포인트 키로 변환한다."""
    for keyword, api_key in PROPERTY_TYPE_MAP.items():
        if keyword in property_type_text:
            return api_key
    return "아파트매매"


async def fetch_transactions(
    lawd_cd: str,
    deal_ymd: str,
    property_type: str = "아파트매매",
) -> list[dict]:
    """국토교통부 실거래가 API를 호출한다.

    Args:
        lawd_cd: 법정동코드 5자리
        deal_ymd: 계약년월 (YYYYMM)
        property_type: API_ENDPOINTS 키 (예: "아파트매매")

    Returns:
        거래 내역 dict 리스트
    """
    endpoint = API_ENDPOINTS.get(property_type, API_ENDPOINTS["아파트매매"])
    params = {
        "serviceKey": settings.molit_api_key,
        "LAWD_CD": lawd_cd,
        "DEAL_YMD": deal_ymd,
        "pageNo": 1,
        "numOfRows": 1000,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(f"{MOLIT_BASE_URL}{endpoint}", params=params)
        response.raise_for_status()

    return parse_xml_response(response.text)
