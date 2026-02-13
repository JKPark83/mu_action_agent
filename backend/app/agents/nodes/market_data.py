"""시세 분석 에이전트 노드 - 실거래가 수집 및 시세 분석"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta
from statistics import mean

from app.agents.state import AgentState
from app.agents.tools.address_converter import address_to_lawd_code
from app.agents.tools.real_estate_api import fetch_transactions, resolve_property_type
from app.schemas.market import MarketDataResult, MonthlyPrice, RentTransaction, Transaction

logger = logging.getLogger(__name__)

# ㎡ → 평 변환 계수
SQM_TO_PYEONG = 3.305785


# ---------------------------------------------------------------------------
# 1. 필터링 유틸리티
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


def filter_by_building_name(
    transactions: list[dict],
    building_name: str,
) -> list[dict]:
    """단지명으로 거래 내역을 필터링한다 (양방향 부분 매칭)."""
    if not building_name or len(building_name) < 2:
        return transactions
    return [
        t for t in transactions
        if building_name in t.get("아파트", "") or t.get("아파트", "") in building_name
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
# 3. 매매 시세 분석
# ---------------------------------------------------------------------------


def analyze_trade_data(
    transactions: list[dict],
    target_area: float,
    appraised_value: int = 0,
) -> tuple[MarketDataResult, int]:
    """매매 거래 데이터를 분석한다. (MarketDataResult, 평균매매가) 반환."""
    # 면적 필터: 10% → 30% → 전체 fallback
    filtered = filter_by_area(transactions, target_area, tolerance=0.1)
    if not filtered and target_area > 0:
        logger.info("면적 ±10%% 필터 결과 0건 → ±30%%로 완화 (target=%.1f㎡)", target_area)
        filtered = filter_by_area(transactions, target_area, tolerance=0.3)
    if not filtered:
        if target_area > 0:
            logger.info("면적 ±30%% 필터 결과 0건 → 전체 거래 %d건 사용", len(transactions))
        filtered = transactions

    if not filtered:
        return MarketDataResult(confidence_score=0.0), 0

    prices = [t["거래금액"] for t in filtered]
    avg_price = int(mean(prices))
    price_per_sqm_list = [
        t["거래금액"] / t["전용면적"] for t in filtered if t["전용면적"] > 0
    ]
    avg_per_sqm = int(mean(price_per_sqm_list)) if price_per_sqm_list else 0
    avg_per_pyeong = int(avg_per_sqm * SQM_TO_PYEONG)

    gap = (avg_price - appraised_value) / appraised_value if appraised_value > 0 else 0.0
    trend = calculate_price_trend(filtered)

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

    # 전체 필터링된 거래에서 월별 평균 계산 (차트용)
    monthly_avgs = compute_monthly_averages(filtered)

    result = MarketDataResult(
        recent_transactions=recent,
        monthly_averages=monthly_avgs,
        avg_price_per_pyeong=avg_per_pyeong,
        price_range_low=min(prices),
        price_range_high=max(prices),
        price_trend=trend,
        appraisal_vs_market_gap=round(gap, 4),
        confidence_score=min(len(filtered) / 10, 1.0),
    )
    return result, avg_price


# ---------------------------------------------------------------------------
# 4. 전월세 분석
# ---------------------------------------------------------------------------


def analyze_rent_data(
    rent_transactions: list[dict],
    avg_trade_price: int,
) -> tuple[float, int, int, list[RentTransaction]]:
    """전월세 데이터를 분석한다.

    Returns:
        (전세가율, 평균 전세보증금, 평균 월세, 최근 전월세 거래 리스트)
    """
    jeonse = [t for t in rent_transactions if t.get("월세금액", 0) == 0 and t.get("보증금액", 0) > 0]
    wolse = [t for t in rent_transactions if t.get("월세금액", 0) > 0]

    avg_jeonse = int(mean([t["보증금액"] for t in jeonse])) if jeonse else 0
    avg_monthly = int(mean([t["월세금액"] for t in wolse])) if wolse else 0
    jeonse_ratio = avg_jeonse / avg_trade_price if avg_trade_price > 0 and avg_jeonse > 0 else 0.0

    recent_rent: list[RentTransaction] = []
    for t in rent_transactions[:20]:
        recent_rent.append(
            RentTransaction(
                address=t.get("법정동", ""),
                area=t["전용면적"],
                deposit=t.get("보증금액", 0),
                monthly_rent=t.get("월세금액", 0),
                transaction_date=f"{t['년']}-{t['월'].zfill(2)}-{t['일'].zfill(2)}",
                contract_type=t.get("계약구분", ""),
            )
        )

    return jeonse_ratio, avg_jeonse, avg_monthly, recent_rent


# ---------------------------------------------------------------------------
# 5. 데이터 수집 헬퍼
# ---------------------------------------------------------------------------


def compute_monthly_averages(transactions: list[dict]) -> list[MonthlyPrice]:
    """거래 데이터를 월별 평균가로 집계한다."""
    monthly: dict[str, list[int]] = {}
    for t in transactions:
        key = f"{t['년']}-{t['월'].zfill(2)}"
        monthly.setdefault(key, []).append(t["거래금액"])
    return [
        MonthlyPrice(date=k, price=int(mean(v)))
        for k, v in sorted(monthly.items())
    ]


async def _collect_transactions(
    lawd_code: str,
    base_type: str,
    transaction_type: str,
    months: int = 12,
) -> list[dict]:
    """최근 N개월간 거래 데이터를 병렬로 수집한다."""
    today = date.today()
    # 중복 제거된 연월 목록 생성
    deal_ymds: set[str] = set()
    for months_ago in range(months):
        target_date = today - timedelta(days=30 * months_ago)
        deal_ymds.add(target_date.strftime("%Y%m"))

    sem = asyncio.Semaphore(10)

    async def fetch_one(deal_ymd: str) -> list[dict]:
        async with sem:
            try:
                return await fetch_transactions(lawd_code, deal_ymd, base_type, transaction_type)
            except Exception as exc:
                logger.warning("  MOLIT %s API 호출 실패 [%s]: %s", transaction_type, deal_ymd, exc)
                return []

    results = await asyncio.gather(*[fetch_one(ymd) for ymd in sorted(deal_ymds, reverse=True)])
    return [t for txns in results for t in txns]


# ---------------------------------------------------------------------------
# 6. 에이전트 노드
# ---------------------------------------------------------------------------


async def market_data_node(state: AgentState) -> dict:
    """시장 데이터 수집 에이전트 노드.

    처리 흐름:
    1. state에서 소재지, 면적, 부동산 유형 가져오기
    2. 주소 → 법정동코드 변환
    3. 최근 12개월간 매매 + 전월세 실거래가 API 호출
    4. 아파트: 단지명 필터링 / 그 외: 면적 기반 필터링
    5. MarketDataResult를 partial dict로 반환
    """
    new_errors: list[str] = []
    registry = state.get("registry")

    if not registry:
        new_errors.append("시세분석 실패: 소재지 정보 없음")
        result_dict: dict = {"market_data": None}
        if new_errors:
            result_dict["errors"] = new_errors
        return result_dict

    try:
        address = registry.property_address
        target_area = registry.area or 0.0
        base_type = resolve_property_type(registry.property_type)
        building_name = getattr(registry, "building_name", None) or ""

        # 아파트인데 building_name이 없으면 주소에서 추출 시도
        if not building_name and base_type == "아파트":
            parts = address.split()
            for part in parts:
                if len(part) >= 4 and not part.endswith(("시", "구", "동", "로", "길")) and not part[0].isdigit():
                    building_name = part
                    break

        lawd_code = address_to_lawd_code(address)
        if not lawd_code:
            new_errors.append(f"시세분석 실패: 법정동코드 변환 실패 ({address})")
            result_dict = {"market_data": None}
            if new_errors:
                result_dict["errors"] = new_errors
            return result_dict

        logger.info(
            "시세분석 시작: %s (법정동코드=%s, 유형=%s, 면적=%.1f㎡, 단지명=%s)",
            address, lawd_code, base_type, target_area, building_name or "(없음)",
        )

        # === 매매 + 전월세 데이터 수집 (매매는 5년치) ===
        all_trade = await _collect_transactions(lawd_code, base_type, "매매", months=60)
        all_rent = await _collect_transactions(lawd_code, base_type, "전월세")

        logger.info("시세 API 수집 결과: 매매 %d건, 전월세 %d건", len(all_trade), len(all_rent))

        # === 아파트: 단지명 필터링 ===
        if base_type == "아파트" and building_name and len(building_name) >= 2:
            filtered_trade = filter_by_building_name(all_trade, building_name)
            filtered_rent = filter_by_building_name(all_rent, building_name)
            logger.info(
                "단지명 필터링 '%s': 매매 %d→%d건, 전월세 %d→%d건",
                building_name,
                len(all_trade), len(filtered_trade),
                len(all_rent), len(filtered_rent),
            )
            all_trade = filtered_trade if len(filtered_trade) >= 3 else all_trade
            all_rent = filtered_rent if len(filtered_rent) >= 3 else all_rent

        if not all_trade and not all_rent:
            new_errors.append(f"시세분석: 거래 데이터 없음 ({address})")
            result_dict = {"market_data": MarketDataResult(confidence_score=0.0)}
            if new_errors:
                result_dict["errors"] = new_errors
            return result_dict

        appraisal = state.get("appraisal")
        appraised_value = appraisal.appraised_value if appraisal else 0

        # === 매매 분석 ===
        trade_result, avg_trade_price = analyze_trade_data(all_trade, target_area, appraised_value)

        # === 전월세 분석 ===
        rent_filtered = filter_by_area(all_rent, target_area, tolerance=0.3) if target_area > 0 else all_rent
        if not rent_filtered:
            rent_filtered = all_rent
        jeonse_ratio, avg_jeonse, avg_monthly, recent_rent = analyze_rent_data(rent_filtered, avg_trade_price)

        # === 결과 병합 ===
        result = MarketDataResult(
            recent_transactions=trade_result.recent_transactions,
            recent_rent_transactions=recent_rent,
            monthly_averages=trade_result.monthly_averages,
            avg_price_per_pyeong=trade_result.avg_price_per_pyeong,
            price_range_low=trade_result.price_range_low,
            price_range_high=trade_result.price_range_high,
            price_trend=trade_result.price_trend,
            jeonse_ratio=round(jeonse_ratio, 4),
            avg_jeonse_deposit=avg_jeonse,
            avg_monthly_rent=avg_monthly,
            appraisal_vs_market_gap=trade_result.appraisal_vs_market_gap,
            confidence_score=trade_result.confidence_score,
        )

        logger.info(
            "시세분석 완료: 매매 %d건, 전월세 %d건, 평균 평당가 %s원, 전세가율 %.1f%%, 추세=%s",
            len(result.recent_transactions),
            len(result.recent_rent_transactions),
            f"{result.avg_price_per_pyeong:,}",
            result.jeonse_ratio * 100,
            result.price_trend,
        )

        result_dict = {"market_data": result}

    except Exception as exc:
        logger.exception("시세분석 오류")
        new_errors.append(f"시세분석 오류: {exc}")
        result_dict = {"market_data": None}

    if new_errors:
        result_dict["errors"] = new_errors
    return result_dict
