"""Task-03: 시장 데이터 수집 에이전트 단위 테스트

외부 API 호출은 모두 mock 처리하여 외부 의존성 없이 테스트한다.
"""

from __future__ import annotations

import pytest

from app.agents.nodes.market_data import (
    analyze_market_data,
    calculate_price_trend,
    filter_by_area,
    market_data_node,
)
from app.agents.state import AgentState
from app.agents.tools.address_converter import address_to_lawd_code
from app.agents.tools.real_estate_api import parse_xml_response


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


SAMPLE_XML = """\
<?xml version="1.0" encoding="UTF-8"?>
<response>
  <header>
    <resultCode>00</resultCode>
    <resultMsg>NORMAL SERVICE</resultMsg>
  </header>
  <body>
    <items>
      <item>
        <거래금액> 85,000</거래금액>
        <건축년도>2015</건축년도>
        <년>2025</년>
        <월>6</월>
        <일>15</일>
        <전용면적>84.99</전용면적>
        <층>12</층>
        <아파트>래미안역삼</아파트>
        <법정동>역삼동</법정동>
      </item>
      <item>
        <거래금액> 92,000</거래금액>
        <건축년도>2018</건축년도>
        <년>2025</년>
        <월>7</월>
        <일>3</일>
        <전용면적>84.5</전용면적>
        <층>8</층>
        <아파트>래미안역삼</아파트>
        <법정동>역삼동</법정동>
      </item>
      <item>
        <거래금액> 50,000</거래금액>
        <건축년도>2010</건축년도>
        <년>2025</년>
        <월>7</월>
        <일>10</일>
        <전용면적>59.0</전용면적>
        <층>3</층>
        <아파트>역삼힐스</아파트>
        <법정동>역삼동</법정동>
      </item>
    </items>
  </body>
</response>
"""


def _make_transactions(prices_by_month: dict[tuple[str, str], list[int]]) -> list[dict]:
    """테스트용 거래 데이터를 생성한다."""
    txns = []
    for (year, month), price_list in prices_by_month.items():
        for i, price in enumerate(price_list):
            txns.append({
                "거래금액": price,
                "건축년도": "2020",
                "년": year,
                "월": month,
                "일": str(i + 1),
                "전용면적": 84.99,
                "층": "10",
                "아파트": "테스트아파트",
                "법정동": "역삼동",
            })
    return txns


# ---------------------------------------------------------------------------
# T-1: MOLIT XML 파싱
# ---------------------------------------------------------------------------


def test_parse_xml_response():
    """MOLIT XML 응답을 dict 리스트로 올바르게 파싱한다."""
    result = parse_xml_response(SAMPLE_XML)

    assert len(result) == 3

    # 첫 번째 거래: 85,000만원 → 850,000,000원
    assert result[0]["거래금액"] == 850_000_000
    assert result[0]["전용면적"] == 84.99
    assert result[0]["아파트"] == "래미안역삼"
    assert result[0]["법정동"] == "역삼동"
    assert result[0]["년"] == "2025"
    assert result[0]["월"] == "6"

    # 세 번째 거래: 50,000만원 → 500,000,000원
    assert result[2]["거래금액"] == 500_000_000
    assert result[2]["전용면적"] == 59.0


# ---------------------------------------------------------------------------
# T-2: 주소 → 법정동코드 변환
# ---------------------------------------------------------------------------


def test_address_to_lawd_code():
    """서울특별시 강남구 역삼동 주소 → '11680' 코드 반환."""
    code = address_to_lawd_code("서울특별시 강남구 역삼동 123-45")
    assert code == "11680"


def test_address_to_lawd_code_unknown():
    """매칭되지 않는 주소 → None 반환."""
    code = address_to_lawd_code("알수없는 지역 123")
    assert code is None


# ---------------------------------------------------------------------------
# T-3: 면적 ±10% 필터링
# ---------------------------------------------------------------------------


def test_filter_by_area():
    """면적 ±10% 범위 내 거래만 필터링한다."""
    transactions = parse_xml_response(SAMPLE_XML)
    target_area = 84.99  # 84.99㎡

    filtered = filter_by_area(transactions, target_area, tolerance=0.1)

    # 84.99와 84.5는 ±10% 범위 내, 59.0은 범위 밖
    assert len(filtered) == 2
    for t in filtered:
        assert abs(t["전용면적"] - target_area) / target_area <= 0.1


# ---------------------------------------------------------------------------
# T-4: 가격 추세 (상승)
# ---------------------------------------------------------------------------


def test_price_trend_rising():
    """이전 6개월보다 최근 6개월 평균이 높으면 '상승' 판정."""
    txns = _make_transactions({
        # 이전 6개월 (낮은 가격)
        ("2025", "1"): [800_000_000],
        ("2025", "2"): [810_000_000],
        ("2025", "3"): [805_000_000],
        ("2025", "4"): [815_000_000],
        ("2025", "5"): [800_000_000],
        ("2025", "6"): [810_000_000],
        # 최근 6개월 (높은 가격 — >3% 상승)
        ("2025", "7"): [880_000_000],
        ("2025", "8"): [890_000_000],
        ("2025", "9"): [885_000_000],
        ("2025", "10"): [900_000_000],
        ("2025", "11"): [895_000_000],
        ("2025", "12"): [910_000_000],
    })

    trend = calculate_price_trend(txns)
    assert trend == "상승"


# ---------------------------------------------------------------------------
# T-5: 노드 — registry 없으면 에러
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_market_node_no_registry():
    """registry가 없으면 에러 메시지를 추가한다."""
    state = AgentState(analysis_id="test-no-reg")

    result = await market_data_node(state)

    assert result.market_data is None
    assert len(result.errors) == 1
    assert "소재지" in result.errors[0]
