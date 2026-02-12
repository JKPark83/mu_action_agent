"""시세 분석 에이전트 노드 - 실거래가 수집 및 시세 분석"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from statistics import mean, median

from app.agents.state import AgentState
from app.agents.tools.address_converter import address_to_lawd_code
from app.agents.tools.real_estate_api import fetch_transactions, resolve_property_type
from app.schemas.market import MarketDataResult, Transaction

logger = logging.getLogger(__name__)

# ㎡ → 평 변환 계수
SQM_TO_PYEONG = 3.305785


# ---------------------------------------------------------------------------
# 1. 유사 면적 필터링
# ---------------------------------------------------------------------------


def filter_by_area(
    transactions: list[dict],
    target_area: float,
    tolerance: float = 0.1,
) -> list[dict]:
    """면적 ±tolerance 범위 내 거래만 필터링한다."""
    if target_area <= 0:
        return transactions
    return [
        t
        for t in transactions
        if t["전용면적"] > 0
        and abs(t["전용면적"] - target_area) / target_area <= tolerance
    ]


# ---------------------------------------------------------------------------
# 2. 가격 추세 분석
# ---------------------------------------------------------------------------


def calculate_price_trend(transactions: list[dict]) -> str:
    """월별 평균가를 비교하여 추세를 판단한다.

    최근 6개월 평균 vs 이전 6개월 평균 비교:
    - 변화율 > 3%: 상승
    - 변화율 < -3%: 하락
    - 그 외: 보합
    """
    monthly: dict[str, list[int]] = {}
    for t in transactions:
        key = f"{t['년']}-{t['월'].zfill(2)}"
        monthly.setdefault(key, []).append(t["거래금액"])

    monthly_avg = {k: int(mean(v)) for k, v in sorted(monthly.items())}
    values = list(monthly_avg.values())

    if len(values) < 2:
        return "보합"

    if len(values) >= 12:
        recent = mean(values[-6:])
        previous = mean(values[-12:-6])
    else:
        mid = len(values) // 2
        recent = mean(values[mid:])
        previous = mean(values[:mid])

    if previous == 0:
        return "보합"

    change_rate = (recent - previous) / previous * 100

    if change_rate > 3:
        return "상승"
    if change_rate < -3:
        return "하락"
    return "보합"


# ---------------------------------------------------------------------------
# 3. 시세 종합 분석
# ---------------------------------------------------------------------------


def analyze_market_data(
    transactions: list[dict],
    target_area: float,
    appraised_value: int = 0,
) -> MarketDataResult:
    """수집된 거래 데이터를 종합 분석하여 MarketDataResult를 생성한다."""
    filtered = filter_by_area(transactions, target_area)

    if not filtered:
        return MarketDataResult(confidence_score=0.0)

    prices = [t["거래금액"] for t in filtered]
    areas = [t["전용면적"] for t in filtered]

    avg_price = int(mean(prices))
    price_per_sqm_list = [
        t["거래금액"] / t["전용면적"] for t in filtered if t["전용면적"] > 0
    ]
    avg_per_sqm = int(mean(price_per_sqm_list)) if price_per_sqm_list else 0
    avg_per_pyeong = int(avg_per_sqm * SQM_TO_PYEONG)

    # 감정가 대비 시세 갭
    gap = (avg_price - appraised_value) / appraised_value if appraised_value > 0 else 0.0

    # 추세
    trend = calculate_price_trend(filtered)

    # 최근 거래 20건을 Transaction 객체로 변환
    recent = []
    for t in filtered[:20]:
        pyeong_price = int(t["거래금액"] / t["전용면적"] * SQM_TO_PYEONG) if t["전용면적"] > 0 else 0
        recent.append(
            Transaction(
                address=t.get("법정동", ""),
                area=t["전용면적"],
                price=t["거래금액"],
                price_per_pyeong=pyeong_price,
                transaction_date=f"{t['년']}-{t['월'].zfill(2)}-{t['일'].zfill(2)}",
            )
        )

    return MarketDataResult(
        recent_transactions=recent,
        avg_price_per_pyeong=avg_per_pyeong,
        price_range_low=min(prices),
        price_range_high=max(prices),
        price_trend=trend,
        jeonse_ratio=0.0,  # 전세 데이터 별도 수집 시 계산
        appraisal_vs_market_gap=round(gap, 4),
        confidence_score=min(len(filtered) / 10, 1.0),
    )


# ---------------------------------------------------------------------------
# 4. 에이전트 노드
# ---------------------------------------------------------------------------


async def market_data_node(state: AgentState) -> AgentState:
    """시장 데이터 수집 에이전트 노드.

    처리 흐름:
    1. state에서 소재지, 면적, 부동산 유형 가져오기
    2. 주소 → 법정동코드 변환
    3. 최근 12개월간 월별 실거래가 API 호출
    4. 유사 거래 필터링 및 통계 분석
    5. MarketDataResult 생성하여 state에 저장
    """
    errors: list[str] = list(state.errors)
    registry = state.registry

    if not registry:
        errors.append("시세분석 실패: 소재지 정보 없음")
        state.market_data = None
        state.errors = errors
        return state

    try:
        address = registry.property_address
        target_area = registry.area or 0.0
        property_type = resolve_property_type(registry.property_type)

        # 법정동코드 변환
        lawd_code = address_to_lawd_code(address)
        if not lawd_code:
            errors.append(f"시세분석 실패: 법정동코드 변환 실패 ({address})")
            state.market_data = None
            state.errors = errors
            return state

        logger.info("시세분석 시작: %s (법정동코드=%s, 면적=%.1f㎡)", address, lawd_code, target_area)

        # 최근 12개월 데이터 수집
        all_transactions: list[dict] = []
        today = date.today()
        for months_ago in range(12):
            target_date = today - timedelta(days=30 * months_ago)
            deal_ymd = target_date.strftime("%Y%m")
            try:
                txns = await fetch_transactions(lawd_code, deal_ymd, property_type)
                all_transactions.extend(txns)
            except Exception as exc:
                logger.warning("API 호출 실패 (%s): %s", deal_ymd, exc)
                continue

        if not all_transactions:
            errors.append(f"시세분석: 거래 데이터 없음 ({address})")
            state.market_data = MarketDataResult(confidence_score=0.0)
            state.errors = errors
            return state

        # 감정가
        appraised_value = state.appraisal.appraised_value if state.appraisal else 0

        # 분석
        result = analyze_market_data(all_transactions, target_area, appraised_value)
        logger.info(
            "시세분석 완료: 거래 %d건, 평균 평당가 %s원, 추세=%s",
            len(result.recent_transactions),
            f"{result.avg_price_per_pyeong:,}",
            result.price_trend,
        )

        state.market_data = result

    except Exception as exc:
        logger.exception("시세분석 오류")
        errors.append(f"시세분석 오류: {exc}")
        state.market_data = None

    state.errors = errors
    return state
