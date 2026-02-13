"""국토교통부 공공데이터 API 클라이언트"""

from __future__ import annotations

import logging
from urllib.parse import quote, unquote, urlencode
import xml.etree.ElementTree as ET

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

MOLIT_BASE_URL = "https://apis.data.go.kr/1613000"

# 부동산 유형별 API 경로 (공공데이터포털 신규 엔드포인트)
# 키 형식: "{부동산유형}{거래유형}" (예: "아파트매매", "아파트전월세")
API_ENDPOINTS: dict[str, str] = {
    "아파트매매": "/RTMSDataSvcAptTrade/getRTMSDataSvcAptTrade",
    "아파트전월세": "/RTMSDataSvcAptRent/getRTMSDataSvcAptRent",
    "연립다세대매매": "/RTMSDataSvcRHTrade/getRTMSDataSvcRHTrade",
    "연립다세대전월세": "/RTMSDataSvcRHRent/getRTMSDataSvcRHRent",
    "단독다가구매매": "/RTMSDataSvcSHTrade/getRTMSDataSvcSHTrade",
    "단독다가구전월세": "/RTMSDataSvcSHRent/getRTMSDataSvcSHRent",
    "오피스텔매매": "/RTMSDataSvcOffiTrade/getRTMSDataSvcOffiTrade",
    "오피스텔전월세": "/RTMSDataSvcOffiRent/getRTMSDataSvcOffiRent",
}

# 부동산 유형 문자열 → base type 매핑
PROPERTY_TYPE_MAP: dict[str, str] = {
    "아파트": "아파트",
    "공동주택": "아파트",
    "연립": "연립다세대",
    "다세대": "연립다세대",
    "빌라": "연립다세대",
    "단독": "단독다가구",
    "다가구": "단독다가구",
    "오피스텔": "오피스텔",
}


def _parse_int_amount(text: str | None) -> int:
    """만원 단위 금액 문자열을 원 단위 정수로 변환한다."""
    raw = (text or "0").strip().replace(",", "")
    try:
        return int(raw) * 10_000
    except ValueError:
        return 0


def _parse_float(text: str | None) -> float:
    """숫자 문자열을 float로 변환한다."""
    raw = (text or "0").strip()
    try:
        return float(raw)
    except ValueError:
        return 0.0


def _text(item: ET.Element, *tag_names: str) -> str:
    """여러 태그명 중 첫 번째로 값이 있는 것을 반환한다 (한글/영어 호환)."""
    for tag in tag_names:
        val = (item.findtext(tag) or "").strip()
        if val:
            return val
    return ""


def parse_xml_response(xml_text: str, response_type: str = "trade") -> list[dict]:
    """MOLIT API XML 응답을 dict 리스트로 변환한다.

    Args:
        xml_text: XML 응답 문자열
        response_type: "trade" (매매) 또는 "rent" (전월세)
    """
    root = ET.fromstring(xml_text)
    items = root.findall(".//item")

    transactions: list[dict] = []
    for item in items:
        record: dict = {
            "전용면적": _parse_float(_text(item, "excluUseAr", "전용면적")),
            "건축년도": _text(item, "buildYear", "건축년도"),
            "년": _text(item, "dealYear", "계약년도", "년"),
            "월": _text(item, "dealMonth", "계약월", "월"),
            "일": _text(item, "dealDay", "계약일", "일"),
            "층": _text(item, "floor", "층"),
            "아파트": _text(item, "aptNm", "단지명", "아파트", "연립다세대"),
            "법정동": _text(item, "umdNm", "법정동"),
        }

        if response_type == "rent":
            record["보증금액"] = _parse_int_amount(_text(item, "deposit", "보증금액"))
            record["월세금액"] = _parse_int_amount(_text(item, "monthlyRent", "월세금액"))
            record["계약구분"] = _text(item, "contractType", "계약구분")
            record["거래금액"] = record["보증금액"]
        else:
            record["거래금액"] = _parse_int_amount(_text(item, "dealAmount", "거래금액"))

        transactions.append(record)

    return transactions


def resolve_property_type(property_type_text: str) -> str:
    """부동산 유형 문자열을 base type으로 변환한다."""
    for keyword, base_type in PROPERTY_TYPE_MAP.items():
        if keyword in property_type_text:
            logger.info("부동산 유형 매핑: '%s' → %s", property_type_text, base_type)
            return base_type
    logger.info("부동산 유형 매핑: '%s' → 아파트 (기본값)", property_type_text)
    return "아파트"


async def fetch_transactions(
    lawd_cd: str,
    deal_ymd: str,
    property_type: str = "아파트",
    transaction_type: str = "매매",
) -> list[dict]:
    """국토교통부 실거래가 API를 호출한다.

    Args:
        lawd_cd: 법정동코드 5자리
        deal_ymd: 계약년월 (YYYYMM)
        property_type: base type (예: "아파트", "연립다세대")
        transaction_type: "매매" 또는 "전월세"

    Returns:
        거래 내역 dict 리스트
    """
    endpoint_key = f"{property_type}{transaction_type}"
    endpoint = API_ENDPOINTS.get(endpoint_key)
    if not endpoint:
        logger.warning("지원하지 않는 API 유형: %s", endpoint_key)
        return []

    # serviceKey의 +, /, = 등 특수문자를 percent-encoding 처리
    raw_key = unquote(settings.molit_api_key)
    encoded_key = quote(raw_key, safe="")
    other_params = urlencode({
        "LAWD_CD": lawd_cd,
        "DEAL_YMD": deal_ymd,
        "pageNo": 1,
        "numOfRows": 1000,
    })
    url = f"{MOLIT_BASE_URL}{endpoint}?serviceKey={encoded_key}&{other_params}"

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(url)
        response.raise_for_status()

    resp_type = "rent" if transaction_type == "전월세" else "trade"
    transactions = parse_xml_response(response.text, response_type=resp_type)
    logger.debug("  MOLIT API [%s] %s %s: %d건", deal_ymd, property_type, transaction_type, len(transactions))
    return transactions
