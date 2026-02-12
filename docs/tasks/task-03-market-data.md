# Task-03: 시장 데이터 수집 에이전트 구현

> **참조 스펙**: PRD-03 전체
> **예상 작업 시간**: 5~7시간
> **선행 작업**: Task-01 (문서 파싱 - 소재지/면적 정보 필요)
> **변경 파일 수**: 3~4개

---

## 목차

1. [국토교통부 실거래가 API 클라이언트](#1-국토교통부-실거래가-api-클라이언트)
2. [주소 → 법정동코드 변환](#2-주소--법정동코드-변환)
3. [시세 분석 로직](#3-시세-분석-로직)
4. [에이전트 노드 구현](#4-에이전트-노드-구현)
5. [테스트 가이드](#5-테스트-가이드)

---

## 1. 국토교통부 실거래가 API 클라이언트

### 1.1 API 호출 구현

> 파일: `backend/app/agents/tools/real_estate_api.py`

```python
import httpx
import xml.etree.ElementTree as ET

MOLIT_BASE_URL = "http://openapi.molit.go.kr"

# 부동산 유형별 API 경로
API_ENDPOINTS = {
    "아파트매매": "/OpenAPI_ToolInstall498/service/rest/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev",
    "아파트전월세": "/OpenAPI_ToolInstall498/service/rest/RTMSDataSvcAptRent/getRTMSDataSvcAptRent",
    "연립다세대": "/OpenAPI_ToolInstall498/service/rest/RTMSDataSvcRHTradeDev/getRTMSDataSvcRHTradeDev",
    "단독다가구": "/OpenAPI_ToolInstall498/service/rest/RTMSDataSvcSHTradeDev/getRTMSDataSvcSHTradeDev",
    "오피스텔": "/OpenAPI_ToolInstall498/service/rest/RTMSDataSvcOffiTradeDev/getRTMSDataSvcOffiTradeDev",
}

async def fetch_transactions(
    lawd_cd: str,
    deal_ymd: str,
    property_type: str = "아파트매매",
) -> list[dict]:
    """
    국토교통부 실거래가 API 호출

    Args:
        lawd_cd: 법정동코드 5자리
        deal_ymd: 계약년월 (YYYYMM)
        property_type: 부동산 유형
    """
    endpoint = API_ENDPOINTS.get(property_type)
    params = {
        "serviceKey": settings.MOLIT_API_KEY,
        "LAWD_CD": lawd_cd,
        "DEAL_YMD": deal_ymd,
        "pageNo": 1,
        "numOfRows": 1000,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.get(f"{MOLIT_BASE_URL}{endpoint}", params=params)
        response.raise_for_status()

    return parse_xml_response(response.text)
```

### 1.2 XML 응답 파싱

```python
def parse_xml_response(xml_text: str) -> list[dict]:
    """MOLIT API XML 응답을 dict 리스트로 변환"""
    root = ET.fromstring(xml_text)
    items = root.findall(".//item")

    transactions = []
    for item in items:
        transactions.append({
            "거래금액": int(item.findtext("거래금액", "0").strip().replace(",", "")),
            "건축년도": item.findtext("건축년도", ""),
            "년": item.findtext("년", ""),
            "월": item.findtext("월", ""),
            "일": item.findtext("일", ""),
            "전용면적": float(item.findtext("전용면적", "0")),
            "층": item.findtext("층", ""),
            "아파트": item.findtext("아파트", "") or item.findtext("연립다세대", ""),
            "법정동": item.findtext("법정동", ""),
        })
    return transactions
```

---

## 2. 주소 → 법정동코드 변환

### 2.1 법정동코드 데이터 로드

```python
# backend/app/agents/tools/address_converter.py

import csv
from pathlib import Path

# 법정동코드 파일 (행정안전부 제공)
LAWD_CODE_FILE = Path(__file__).parent / "data" / "lawd_code.csv"

_code_cache: dict[str, str] = {}

def load_lawd_codes() -> dict[str, str]:
    """법정동코드 CSV → {동이름: 5자리코드} 딕셔너리"""
    global _code_cache
    if _code_cache:
        return _code_cache

    with open(LAWD_CODE_FILE, encoding="utf-8") as f:
        reader = csv.reader(f)
        for row in reader:
            code, name, is_exist = row[0], row[1], row[2]
            if is_exist == "존재":
                _code_cache[name.strip()] = code[:5]

    return _code_cache

def address_to_lawd_code(address: str) -> str | None:
    """
    주소 문자열에서 법정동코드 5자리 추출
    예: '서울특별시 강남구 역삼동' → '11680'
    """
    codes = load_lawd_codes()
    # 시/군/구 단위로 매칭
    for name, code in codes.items():
        if name in address:
            return code
    return None
```

---

## 3. 시세 분석 로직

### 3.1 유사 거래 필터링 및 통계

```python
from datetime import date, timedelta
from statistics import mean, median

def analyze_market_data(
    transactions: list[dict],
    target_area: float,
    area_tolerance: float = 0.1,
) -> MarketDataResult:
    """
    1. 유사 면적(±10%) 거래만 필터링
    2. 평균/중위/최고/최저 가격 산출
    3. ㎡당 단가 계산
    4. 월별 가격 추이 분석
    """
    # 면적 필터
    filtered = [
        t for t in transactions
        if abs(t["전용면적"] - target_area) / target_area <= area_tolerance
    ]

    prices = [t["거래금액"] for t in filtered]

    price_range = PriceRange(
        min_price=min(prices) if prices else 0,
        max_price=max(prices) if prices else 0,
        avg_price=int(mean(prices)) if prices else 0,
        median_price=int(median(prices)) if prices else 0,
    )

    avg_per_sqm = int(mean(t["거래금액"] / t["전용면적"] for t in filtered)) if filtered else 0

    # 월별 추이 분석
    price_trend = calculate_price_trend(filtered)

    return MarketDataResult(
        recent_transactions=filtered[:20],
        avg_price_per_sqm=avg_per_sqm,
        avg_price_per_pyeong=int(avg_per_sqm * 3.305785),
        price_range=price_range,
        price_trend=price_trend,
        data_count=len(filtered),
        confidence_score=min(len(filtered) / 10, 1.0),
        ...
    )
```

### 3.2 가격 추이 분석

```python
def calculate_price_trend(transactions: list[dict]) -> PriceTrend:
    """월별 평균가 → 상승/하락/보합 판단"""
    monthly = {}
    for t in transactions:
        key = f"{t['년']}-{t['월'].zfill(2)}"
        monthly.setdefault(key, []).append(t["거래금액"])

    monthly_avg = {k: int(mean(v)) for k, v in sorted(monthly.items())}

    # 최근 6개월 vs 이전 6개월 비교
    values = list(monthly_avg.values())
    if len(values) >= 12:
        recent = mean(values[-6:])
        previous = mean(values[-12:-6])
        change_rate = (recent - previous) / previous * 100
    else:
        change_rate = 0.0

    direction = "상승" if change_rate > 3 else ("하락" if change_rate < -3 else "보합")

    return PriceTrend(
        direction=direction,
        change_rate_6m=round(change_rate, 1),
        monthly_data=monthly_avg,
        ...
    )
```

---

## 4. 에이전트 노드 구현

### 4.1 market_data 노드

> 파일: `backend/app/agents/nodes/market_data.py`

```python
async def market_data_node(state: AgentState) -> AgentState:
    """
    처리 흐름:
    1. state에서 소재지, 면적, 부동산 유형 가져오기
    2. 주소 → 법정동코드 변환
    3. 최근 3년간 월별 실거래가 API 호출
    4. 유사 거래 필터링 및 통계 분석
    5. 감정가 대비 시세 분석
    6. MarketDataResult 생성
    """
    registry = state.get("registry")
    appraisal = state.get("appraisal")

    if not registry:
        return {**state, "market_data": None, "errors": state.get("errors", []) + ["소재지 정보 없음"]}

    address = registry.property_address
    area = registry.area
    lawd_code = address_to_lawd_code(address)

    if not lawd_code:
        return {**state, "market_data": None, "errors": state.get("errors", []) + ["법정동코드 변환 실패"]}

    # 최근 3년 데이터 수집
    all_transactions = []
    today = date.today()
    for months_ago in range(36):
        target = today - timedelta(days=30 * months_ago)
        deal_ymd = target.strftime("%Y%m")
        try:
            txns = await fetch_transactions(lawd_code, deal_ymd)
            all_transactions.extend(txns)
        except Exception:
            continue  # API 실패 시 건너뜀

    result = analyze_market_data(all_transactions, area)
    return {**state, "market_data": result}
```

---

## 5. 테스트 가이드

### 5.1 테스트 케이스

| ID | 테스트명 | 설명 | 기대 결과 |
|:---:|:---|:---|:---|
| T-1 | `test_parse_xml_response` | MOLIT XML 파싱 | dict 리스트 반환 |
| T-2 | `test_address_to_lawd_code` | 강남구 역삼동 → 코드 | "11680" 반환 |
| T-3 | `test_filter_by_area` | 면적 ±10% 필터 | 범위 내 거래만 |
| T-4 | `test_price_trend_rising` | 상승 추세 데이터 | direction="상승" |
| T-5 | `test_market_node_no_address` | 주소 없음 | 에러 메시지 추가 |

### 5.2 테스트 실행

```bash
cd backend
uv run pytest tests/unit/agents/test_market_data.py -v
```

---

## 파일 변경 요약

### 수정 파일

| 파일 경로 | 변경 내용 |
|:---|:---|
| `backend/app/agents/tools/real_estate_api.py` | MOLIT API 클라이언트 구현 |
| `backend/app/agents/nodes/market_data.py` | 시장 데이터 노드 구현 |

### 신규 생성 파일

| 파일 경로 | 설명 |
|:---|:---|
| `backend/app/agents/tools/address_converter.py` | 주소 → 법정동코드 변환 |
| `backend/app/agents/tools/data/lawd_code.csv` | 법정동코드 데이터 파일 |
| `backend/tests/unit/agents/test_market_data.py` | 단위 테스트 |
