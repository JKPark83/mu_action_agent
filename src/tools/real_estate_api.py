from __future__ import annotations

import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

import httpx
from dotenv import load_dotenv

from src.models.schemas import MarketDataResponse, TransactionRecord

load_dotenv()

# ---------------------------------------------------------------------------
# 법정동코드 매퍼 – 주요 시군구 ~250개 하드코딩
# ---------------------------------------------------------------------------

LAWD_CODE_MAP: dict[str, str] = {
    # ── 서울특별시 ──
    "서울특별시 종로구": "11110",
    "서울특별시 중구": "11140",
    "서울특별시 용산구": "11170",
    "서울특별시 성동구": "11200",
    "서울특별시 광진구": "11215",
    "서울특별시 동대문구": "11230",
    "서울특별시 중랑구": "11260",
    "서울특별시 성북구": "11290",
    "서울특별시 강북구": "11305",
    "서울특별시 도봉구": "11320",
    "서울특별시 노원구": "11350",
    "서울특별시 은평구": "11380",
    "서울특별시 서대문구": "11410",
    "서울특별시 마포구": "11440",
    "서울특별시 양천구": "11470",
    "서울특별시 강서구": "11500",
    "서울특별시 구로구": "11530",
    "서울특별시 금천구": "11545",
    "서울특별시 영등포구": "11560",
    "서울특별시 동작구": "11590",
    "서울특별시 관악구": "11620",
    "서울특별시 서초구": "11650",
    "서울특별시 강남구": "11680",
    "서울특별시 송파구": "11710",
    "서울특별시 강동구": "11740",
    # ── 부산광역시 ──
    "부산광역시 중구": "26110",
    "부산광역시 서구": "26140",
    "부산광역시 동구": "26170",
    "부산광역시 영도구": "26200",
    "부산광역시 부산진구": "26230",
    "부산광역시 동래구": "26260",
    "부산광역시 남구": "26290",
    "부산광역시 북구": "26320",
    "부산광역시 해운대구": "26350",
    "부산광역시 사하구": "26380",
    "부산광역시 금정구": "26410",
    "부산광역시 강서구": "26440",
    "부산광역시 연제구": "26470",
    "부산광역시 수영구": "26500",
    "부산광역시 사상구": "26530",
    "부산광역시 기장군": "26710",
    # ── 대구광역시 ──
    "대구광역시 중구": "27110",
    "대구광역시 동구": "27140",
    "대구광역시 서구": "27170",
    "대구광역시 남구": "27200",
    "대구광역시 북구": "27230",
    "대구광역시 수성구": "27260",
    "대구광역시 달서구": "27290",
    "대구광역시 달성군": "27710",
    "대구광역시 군위군": "27720",
    # ── 인천광역시 ──
    "인천광역시 중구": "28110",
    "인천광역시 동구": "28140",
    "인천광역시 미추홀구": "28177",
    "인천광역시 연수구": "28185",
    "인천광역시 남동구": "28200",
    "인천광역시 부평구": "28237",
    "인천광역시 계양구": "28245",
    "인천광역시 서구": "28260",
    "인천광역시 강화군": "28710",
    "인천광역시 옹진군": "28720",
    # ── 광주광역시 ──
    "광주광역시 동구": "29110",
    "광주광역시 서구": "29140",
    "광주광역시 남구": "29155",
    "광주광역시 북구": "29170",
    "광주광역시 광산구": "29200",
    # ── 대전광역시 ──
    "대전광역시 동구": "30110",
    "대전광역시 중구": "30140",
    "대전광역시 서구": "30170",
    "대전광역시 유성구": "30200",
    "대전광역시 대덕구": "30230",
    # ── 울산광역시 ──
    "울산광역시 중구": "31110",
    "울산광역시 남구": "31140",
    "울산광역시 동구": "31170",
    "울산광역시 북구": "31200",
    "울산광역시 울주군": "31710",
    # ── 세종특별자치시 ──
    "세종특별자치시": "36110",
    # ── 경기도 ──
    "경기도 수원시 장안구": "41111",
    "경기도 수원시 권선구": "41113",
    "경기도 수원시 팔달구": "41115",
    "경기도 수원시 영통구": "41117",
    "경기도 성남시 수정구": "41131",
    "경기도 성남시 중원구": "41133",
    "경기도 성남시 분당구": "41135",
    "경기도 의정부시": "41150",
    "경기도 안양시 만안구": "41171",
    "경기도 안양시 동안구": "41173",
    "경기도 부천시": "41190",
    "경기도 광명시": "41210",
    "경기도 평택시": "41220",
    "경기도 동두천시": "41250",
    "경기도 안산시 상록구": "41271",
    "경기도 안산시 단원구": "41273",
    "경기도 고양시 덕양구": "41281",
    "경기도 고양시 일산동구": "41285",
    "경기도 고양시 일산서구": "41287",
    "경기도 과천시": "41290",
    "경기도 구리시": "41310",
    "경기도 남양주시": "41360",
    "경기도 오산시": "41370",
    "경기도 시흥시": "41390",
    "경기도 군포시": "41410",
    "경기도 의왕시": "41430",
    "경기도 하남시": "41450",
    "경기도 용인시 처인구": "41461",
    "경기도 용인시 기흥구": "41463",
    "경기도 용인시 수지구": "41465",
    "경기도 파주시": "41480",
    "경기도 이천시": "41500",
    "경기도 안성시": "41550",
    "경기도 김포시": "41570",
    "경기도 화성시": "41590",
    "경기도 광주시": "41610",
    "경기도 양주시": "41630",
    "경기도 포천시": "41650",
    "경기도 여주시": "41670",
    "경기도 연천군": "41800",
    "경기도 가평군": "41820",
    "경기도 양평군": "41830",
    # ── 강원특별자치도 ──
    "강원특별자치도 춘천시": "51110",
    "강원특별자치도 원주시": "51130",
    "강원특별자치도 강릉시": "51150",
    "강원특별자치도 동해시": "51170",
    "강원특별자치도 태백시": "51190",
    "강원특별자치도 속초시": "51210",
    "강원특별자치도 삼척시": "51230",
    "강원특별자치도 홍천군": "51720",
    "강원특별자치도 횡성군": "51730",
    "강원특별자치도 영월군": "51750",
    "강원특별자치도 평창군": "51760",
    "강원특별자치도 정선군": "51770",
    "강원특별자치도 철원군": "51780",
    "강원특별자치도 화천군": "51790",
    "강원특별자치도 양구군": "51800",
    "강원특별자치도 인제군": "51810",
    "강원특별자치도 고성군": "51820",
    "강원특별자치도 양양군": "51830",
    # 강원도 (이전 명칭 호환)
    "강원도 춘천시": "51110",
    "강원도 원주시": "51130",
    "강원도 강릉시": "51150",
    # ── 충청북도 ──
    "충청북도 청주시 상당구": "43111",
    "충청북도 청주시 서원구": "43112",
    "충청북도 청주시 흥덕구": "43113",
    "충청북도 청주시 청원구": "43114",
    "충청북도 충주시": "43130",
    "충청북도 제천시": "43150",
    "충청북도 보은군": "43720",
    "충청북도 옥천군": "43730",
    "충청북도 영동군": "43740",
    "충청북도 증평군": "43745",
    "충청북도 진천군": "43750",
    "충청북도 괴산군": "43760",
    "충청북도 음성군": "43770",
    "충청북도 단양군": "43800",
    # ── 충청남도 ──
    "충청남도 천안시 동남구": "44131",
    "충청남도 천안시 서북구": "44133",
    "충청남도 공주시": "44150",
    "충청남도 보령시": "44180",
    "충청남도 아산시": "44200",
    "충청남도 서산시": "44210",
    "충청남도 논산시": "44230",
    "충청남도 계룡시": "44250",
    "충청남도 당진시": "44270",
    "충청남도 금산군": "44710",
    "충청남도 부여군": "44760",
    "충청남도 서천군": "44770",
    "충청남도 청양군": "44790",
    "충청남도 홍성군": "44800",
    "충청남도 예산군": "44810",
    "충청남도 태안군": "44825",
    # ── 전북특별자치도 ──
    "전북특별자치도 전주시 완산구": "52111",
    "전북특별자치도 전주시 덕진구": "52113",
    "전북특별자치도 군산시": "52130",
    "전북특별자치도 익산시": "52140",
    "전북특별자치도 정읍시": "52180",
    "전북특별자치도 남원시": "52190",
    "전북특별자치도 김제시": "52210",
    "전북특별자치도 완주군": "52710",
    "전북특별자치도 진안군": "52720",
    "전북특별자치도 무주군": "52730",
    "전북특별자치도 장수군": "52740",
    "전북특별자치도 임실군": "52750",
    "전북특별자치도 순창군": "52770",
    "전북특별자치도 고창군": "52790",
    "전북특별자치도 부안군": "52800",
    # 전라북도 (이전 명칭 호환)
    "전라북도 전주시 완산구": "52111",
    "전라북도 전주시 덕진구": "52113",
    "전라북도 군산시": "52130",
    "전라북도 익산시": "52140",
    # ── 전라남도 ──
    "전라남도 목포시": "46110",
    "전라남도 여수시": "46130",
    "전라남도 순천시": "46150",
    "전라남도 나주시": "46170",
    "전라남도 광양시": "46230",
    "전라남도 담양군": "46710",
    "전라남도 곡성군": "46720",
    "전라남도 구례군": "46730",
    "전라남도 고흥군": "46770",
    "전라남도 보성군": "46780",
    "전라남도 화순군": "46790",
    "전라남도 장흥군": "46800",
    "전라남도 강진군": "46810",
    "전라남도 해남군": "46820",
    "전라남도 영암군": "46830",
    "전라남도 무안군": "46840",
    "전라남도 함평군": "46860",
    "전라남도 영광군": "46870",
    "전라남도 장성군": "46880",
    "전라남도 완도군": "46890",
    "전라남도 진도군": "46900",
    "전라남도 신안군": "46910",
    # ── 경상북도 ──
    "경상북도 포항시 남구": "47111",
    "경상북도 포항시 북구": "47113",
    "경상북도 경주시": "47130",
    "경상북도 김천시": "47150",
    "경상북도 안동시": "47170",
    "경상북도 구미시": "47190",
    "경상북도 영주시": "47210",
    "경상북도 영천시": "47230",
    "경상북도 상주시": "47250",
    "경상북도 문경시": "47280",
    "경상북도 경산시": "47290",
    "경상북도 의성군": "47730",
    "경상북도 청송군": "47750",
    "경상북도 영양군": "47760",
    "경상북도 영덕군": "47770",
    "경상북도 청도군": "47820",
    "경상북도 고령군": "47830",
    "경상북도 성주군": "47840",
    "경상북도 칠곡군": "47850",
    "경상북도 예천군": "47900",
    "경상북도 봉화군": "47920",
    "경상북도 울진군": "47930",
    "경상북도 울릉군": "47940",
    # ── 경상남도 ──
    "경상남도 창원시 의창구": "48121",
    "경상남도 창원시 성산구": "48123",
    "경상남도 창원시 마산합포구": "48125",
    "경상남도 창원시 마산회원구": "48127",
    "경상남도 창원시 진해구": "48129",
    "경상남도 진주시": "48170",
    "경상남도 통영시": "48220",
    "경상남도 사천시": "48240",
    "경상남도 김해시": "48250",
    "경상남도 밀양시": "48270",
    "경상남도 거제시": "48310",
    "경상남도 양산시": "48330",
    "경상남도 의령군": "48720",
    "경상남도 함안군": "48730",
    "경상남도 창녕군": "48740",
    "경상남도 고성군": "48820",
    "경상남도 남해군": "48840",
    "경상남도 하동군": "48850",
    "경상남도 산청군": "48860",
    "경상남도 함양군": "48870",
    "경상남도 거창군": "48880",
    "경상남도 합천군": "48890",
    # ── 제주특별자치도 ──
    "제주특별자치도 제주시": "50110",
    "제주특별자치도 서귀포시": "50130",
}


class LawdCodeMapper:
    """법정동코드 매퍼 – 주소 문자열에서 시도+시군구를 파싱하여 5자리 코드 반환"""

    def __init__(self) -> None:
        self._map = LAWD_CODE_MAP

    def get_code(self, address: str) -> str | None:
        """주소에서 법정동코드 5자리를 추출한다. 매칭 실패 시 None."""
        address = address.strip()

        # 1) 전체 주소에서 시도+시군구(+구) 부분을 직접 매칭 시도
        for key in sorted(self._map, key=len, reverse=True):
            if key in address:
                return self._map[key]

        # 2) 파싱 시도: "서울 강남구" → "서울특별시 강남구" 등 약칭 변환
        normalized = self._normalize(address)
        for key in sorted(self._map, key=len, reverse=True):
            if key in normalized:
                return self._map[key]

        return None

    @staticmethod
    def _normalize(address: str) -> str:
        """주소 약칭을 정식 명칭으로 변환"""
        replacements = {
            "서울 ": "서울특별시 ",
            "부산 ": "부산광역시 ",
            "대구 ": "대구광역시 ",
            "인천 ": "인천광역시 ",
            "광주 ": "광주광역시 ",
            "대전 ": "대전광역시 ",
            "울산 ": "울산광역시 ",
            "세종 ": "세종특별자치시 ",
            "경기 ": "경기도 ",
            "강원 ": "강원특별자치도 ",
            "충북 ": "충청북도 ",
            "충남 ": "충청남도 ",
            "전북 ": "전북특별자치도 ",
            "전남 ": "전라남도 ",
            "경북 ": "경상북도 ",
            "경남 ": "경상남도 ",
            "제주 ": "제주특별자치도 ",
        }
        result = address
        for short, full in replacements.items():
            result = result.replace(short, full)
        return result


# ---------------------------------------------------------------------------
# 국토부 실거래가 API 클라이언트
# ---------------------------------------------------------------------------

# 물건종류 → API 엔드포인트 매핑
_PROPERTY_ENDPOINT: dict[str, str] = {
    "아파트": "/OpenAPI_ToolInstall498/service/rest/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev",
    "연립다세대": "/OpenAPI_ToolInstall498/service/rest/RTMSDataSvcRHTrade/getRTMSDataSvcRHTrade",
    "단독다가구": "/OpenAPI_ToolInstall498/service/rest/RTMSDataSvcSHTrade/getRTMSDataSvcSHTrade",
    "오피스텔": "/OpenAPI_ToolInstall498/service/rest/RTMSDataSvcOffiTrade/getRTMSDataSvcOffiTrade",
}

_BASE_URL = "http://openapi.molit.go.kr"


class RealEstateAPIClient:
    """국토부 실거래가 공공데이터 API 클라이언트 (httpx 동기)"""

    def __init__(self, service_key: str | None = None) -> None:
        self.service_key = service_key or os.getenv("DATA_GO_KR_API_KEY", "")
        self._client = httpx.Client(timeout=30.0)
        self._lawd = LawdCodeMapper()

    @property
    def has_key(self) -> bool:
        return bool(self.service_key) and self.service_key != "..."

    def get_recent_transactions(
        self,
        property_type: str,
        address: str,
        months: int = 6,
    ) -> MarketDataResponse:
        """최근 N개월 거래 데이터를 조회하여 MarketDataResponse 반환.

        API 키가 없으면 빈 결과를 반환한다 (graceful degradation).
        """
        lawd_cd = self._lawd.get_code(address)
        if lawd_cd is None:
            return MarketDataResponse(
                price_trend_detail=f"주소에서 법정동코드를 찾을 수 없습니다: {address}"
            )

        if not self.has_key:
            return MarketDataResponse(
                price_trend_detail="DATA_GO_KR_API_KEY가 설정되지 않아 실거래가 데이터를 조회할 수 없습니다."
            )

        # 물건종류 정규화
        prop_key = self._resolve_property_key(property_type)
        endpoint = _PROPERTY_ENDPOINT.get(prop_key)
        if endpoint is None:
            return MarketDataResponse(
                price_trend_detail=f"지원하지 않는 물건종류입니다: {property_type}"
            )

        # 최근 N개월 월별 조회
        all_records: list[TransactionRecord] = []
        now = datetime.now()
        date_labels: list[str] = []

        for i in range(months):
            dt = now - timedelta(days=30 * i)
            deal_ymd = dt.strftime("%Y%m")
            date_labels.append(deal_ymd)
            records = self._fetch_month(endpoint, lawd_cd, deal_ymd)
            all_records.extend(records)

        if not all_records:
            return MarketDataResponse(
                data_period=f"{date_labels[-1]}~{date_labels[0]}",
                price_trend_detail="조회 기간 내 거래 데이터가 없습니다.",
            )

        # 통계 계산
        total_amount = sum(r.deal_amount for r in all_records)
        total_area = sum(r.area_m2 for r in all_records)
        avg_per_m2 = int(total_amount / total_area) if total_area > 0 else 0

        # 시세 추이 (전반 3개월 vs 후반 3개월)
        mid = months // 2
        mid_ymd = (now - timedelta(days=30 * mid)).strftime("%Y%m")
        recent = [r for r in all_records if r.deal_date.replace("-", "") >= mid_ymd]
        older = [r for r in all_records if r.deal_date.replace("-", "") < mid_ymd]

        if recent and older:
            avg_recent = sum(r.deal_amount / r.area_m2 for r in recent) / len(recent)
            avg_older = sum(r.deal_amount / r.area_m2 for r in older) / len(older)
            change = (avg_recent - avg_older) / avg_older * 100 if avg_older else 0
            if change > 2:
                trend, detail = "상승", f"최근 {mid}개월 대비 +{change:.1f}% 상승"
            elif change < -2:
                trend, detail = "하락", f"최근 {mid}개월 대비 {change:.1f}% 하락"
            else:
                trend, detail = "보합", f"최근 {mid}개월 대비 {change:+.1f}% 보합"
        else:
            trend, detail = "데이터 부족", "추이 판단을 위한 충분한 데이터가 없습니다."

        return MarketDataResponse(
            recent_transactions=all_records,
            avg_price_per_m2=avg_per_m2,
            transaction_volume=len(all_records),
            price_trend=trend,
            price_trend_detail=detail,
            data_period=f"{date_labels[-1]}~{date_labels[0]}",
        )

    def _fetch_month(
        self,
        endpoint: str,
        lawd_cd: str,
        deal_ymd: str,
    ) -> list[TransactionRecord]:
        """단일 월 거래 데이터 조회 (XML 파싱)"""
        params = {
            "serviceKey": self.service_key,
            "LAWD_CD": lawd_cd,
            "DEAL_YMD": deal_ymd,
            "pageNo": "1",
            "numOfRows": "200",
        }
        try:
            resp = self._client.get(f"{_BASE_URL}{endpoint}", params=params)
            resp.raise_for_status()
        except httpx.HTTPError:
            return []

        return self._parse_xml(resp.text, deal_ymd)

    @staticmethod
    def _parse_xml(xml_text: str, fallback_ymd: str) -> list[TransactionRecord]:
        """XML 응답을 TransactionRecord 리스트로 변환"""
        records: list[TransactionRecord] = []
        try:
            root = ET.fromstring(xml_text)
        except ET.ParseError:
            return records

        for item in root.iter("item"):
            try:
                # 거래금액: 만원 단위 문자열 ("30,000") → 원 단위 int
                raw_amount = (item.findtext("거래금액") or item.findtext("dealAmount") or "0")
                amount = int(raw_amount.replace(",", "").strip()) * 10_000

                area_text = (item.findtext("전용면적") or item.findtext("excluUseAr") or "0")
                area = float(area_text.strip())

                year = (item.findtext("년") or item.findtext("dealYear") or fallback_ymd[:4]).strip()
                month = (item.findtext("월") or item.findtext("dealMonth") or fallback_ymd[4:6]).strip()
                deal_date = f"{year}-{int(month):02d}"

                floor_text = item.findtext("층") or item.findtext("floor")
                floor_val = int(floor_text.strip()) if floor_text and floor_text.strip() else None

                bldg = (item.findtext("아파트") or item.findtext("aptNm") or item.findtext("연립다세대") or "")

                records.append(
                    TransactionRecord(
                        deal_date=deal_date,
                        deal_amount=amount,
                        area_m2=area if area > 0 else 1.0,
                        floor=floor_val,
                        building_name=bldg.strip() if bldg else None,
                    )
                )
            except (ValueError, TypeError):
                continue

        return records

    @staticmethod
    def _resolve_property_key(property_type: str) -> str:
        """PropertyType enum 값이나 자유 텍스트를 endpoint 키로 정규화"""
        mapping = {
            "아파트": "아파트",
            "연립다세대": "연립다세대",
            "연립": "연립다세대",
            "다세대": "연립다세대",
            "빌라": "연립다세대",
            "단독다가구": "단독다가구",
            "단독": "단독다가구",
            "다가구": "단독다가구",
            "오피스텔": "오피스텔",
        }
        return mapping.get(property_type, property_type)

    def close(self) -> None:
        self._client.close()
