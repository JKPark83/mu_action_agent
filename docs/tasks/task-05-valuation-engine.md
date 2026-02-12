# Task-05: 가치 평가 엔진 구현

> **참조 스펙**: PRD-05 전체
> **예상 작업 시간**: 6~8시간
> **선행 작업**: Task-02 (권리분석), Task-03 (시장데이터), Task-04 (뉴스분석)
> **변경 파일 수**: 3~4개

---

## 목차

1. [비용 산출 로직](#1-비용-산출-로직)
2. [적정가 산출](#2-적정가-산출)
3. [수익률 분석](#3-수익률-분석)
4. [입찰 추천 판단](#4-입찰-추천-판단)
5. [에이전트 노드 구현](#5-에이전트-노드-구현)
6. [테스트 가이드](#6-테스트-가이드)

---

## 1. 비용 산출 로직

### 1.1 취득세 계산

> 참조: PRD-05 섹션 7 (취득세 산출 기준표)

```python
def calculate_acquisition_tax(
    price: int,
    property_type: str,
    num_houses: int = 1,
    is_regulated_area: bool = False,
) -> int:
    """
    취득세 산출 (부동산 유형/가격대/주택수에 따른 세율 적용)

    주택 1채 기준:
    - 6억 이하: 1%
    - 6~9억: 1~3% (구간별 누진)
    - 9억 초과: 3%
    상가/오피스텔: 4.6%, 토지: 4%
    """
    if property_type in ("상가", "오피스텔"):
        rate = 0.046
    elif property_type == "토지":
        rate = 0.04
    elif num_houses >= 3:
        rate = 0.12 if is_regulated_area else 0.08
    elif num_houses == 2 and is_regulated_area:
        rate = 0.08
    else:
        # 1주택
        if price <= 600_000_000:
            rate = 0.01
        elif price <= 900_000_000:
            rate = 0.01 + (price - 600_000_000) / 300_000_000 * 0.02
        else:
            rate = 0.03

    return int(price * rate)
```

### 1.2 비용 상세 분석

```python
def calculate_cost_breakdown(
    bid_price: int,
    property_type: str,
    assumed_rights_cost: int,
    num_tenants: int,
    has_opposition_tenants: bool,
) -> CostBreakdown:
    """
    전체 비용 산출:
    - 취득세
    - 등록면허세 (취득세의 약 20%)
    - 법무사 비용 (50~100만원)
    - 인수 권리 비용
    - 명도 비용 (임차인 수 × 예상 비용)
    - 수리 비용 (감정평가서 기반 추정)
    - 중개수수료 (매도 시)
    """
    acq_tax = calculate_acquisition_tax(bid_price, property_type)

    return CostBreakdown(
        bid_price=bid_price,
        acquisition_tax=acq_tax,
        registration_fee=int(acq_tax * 0.2),
        legal_fee=800_000,
        assumed_rights_cost=assumed_rights_cost,
        eviction_cost=estimate_eviction_cost(num_tenants, has_opposition_tenants),
        repair_cost=0,  # Claude 추정 또는 감정평가서 기반
        brokerage_fee=int(bid_price * 0.004),  # 0.4% 가정
        capital_gains_tax=0,  # 추후 계산
        total_cost=0,  # 합산
    )

def estimate_eviction_cost(num_tenants: int, has_opposition: bool) -> int:
    """명도 비용 추정: 대항력 있는 임차인당 약 500만원, 없으면 200만원"""
    per_tenant = 5_000_000 if has_opposition else 2_000_000
    return num_tenants * per_tenant
```

---

## 2. 적정가 산출

### 2.1 입찰 적정가

```python
def calculate_bid_price_range(
    estimated_market_value: int,
    assumed_rights_cost: int,
    total_extra_cost: int,
    minimum_bid: int,
) -> BidPriceRange:
    """
    입찰 적정가 = 추정 시세 × 비율 - 인수비용 - 부대비용

    보수적: 시세 × 0.65
    적정:   시세 × 0.75
    공격적: 시세 × 0.85
    """
    conservative = int(estimated_market_value * 0.65) - assumed_rights_cost - total_extra_cost
    moderate = int(estimated_market_value * 0.75) - assumed_rights_cost - total_extra_cost
    aggressive = int(estimated_market_value * 0.85) - assumed_rights_cost - total_extra_cost

    return BidPriceRange(
        conservative=max(conservative, minimum_bid),
        moderate=max(moderate, minimum_bid),
        aggressive=max(aggressive, minimum_bid),
        minimum_bid=minimum_bid,
        calculation_basis=f"추정시세 {estimated_market_value:,}원 기준",
    )
```

### 2.2 매도 적정가

```python
def calculate_sale_price_range(
    market_value: int,
    price_trend_direction: str,
    has_positive_factors: bool,
    has_negative_factors: bool,
) -> SalePriceRange:
    """
    매도 적정가 (시장 동향 보정):
    - 비관적: 시세 × 0.95 (±동향 보정)
    - 기본: 시세 × 1.00
    - 낙관적: 시세 × 1.05~1.10
    """
    trend_adj = 0.0
    if price_trend_direction == "상승":
        trend_adj = 0.03
    elif price_trend_direction == "하락":
        trend_adj = -0.03

    factor_adj = 0.0
    if has_positive_factors:
        factor_adj += 0.02
    if has_negative_factors:
        factor_adj -= 0.02

    return SalePriceRange(
        pessimistic=int(market_value * (0.95 + trend_adj + factor_adj)),
        base=int(market_value * (1.00 + trend_adj + factor_adj)),
        optimistic=int(market_value * (1.07 + trend_adj + factor_adj)),
        holding_period_months=12,
    )
```

---

## 3. 수익률 분석

```python
def calculate_profitability(
    bid_price: int,
    sale_price_range: SalePriceRange,
    total_cost: int,
) -> ProfitabilityAnalysis:
    """
    수익률 = (매도가 - 총투자비용) / 총투자비용 × 100
    """
    total_investment = bid_price + total_cost

    profit_min = sale_price_range.pessimistic - total_investment
    profit_max = sale_price_range.optimistic - total_investment

    roi_conservative = profit_min / total_investment * 100 if total_investment else 0
    roi_moderate = (sale_price_range.base - total_investment) / total_investment * 100 if total_investment else 0
    roi_optimistic = profit_max / total_investment * 100 if total_investment else 0

    holding_years = sale_price_range.holding_period_months / 12
    annual_roi = roi_moderate / holding_years if holding_years else 0

    return ProfitabilityAnalysis(
        total_investment=total_investment,
        expected_profit_min=profit_min,
        expected_profit_max=profit_max,
        roi_conservative=round(roi_conservative, 1),
        roi_moderate=round(roi_moderate, 1),
        roi_optimistic=round(roi_optimistic, 1),
        annual_roi=round(annual_roi, 1),
        rental_yield=None,
    )
```

---

## 4. 입찰 추천 판단

```python
def determine_recommendation(
    risk_level: str,
    roi_moderate: float,
    has_assumed_risk: bool,
) -> tuple[str, str]:
    """
    추천 기준:
    - 추천: 위험도 '하' + 수익률 15% 이상
    - 보류: 위험도 '중' 또는 수익률 5~15%
    - 비추천: 위험도 '상' 또는 수익률 5% 미만 또는 인수 위험 존재
    """
    if risk_level == "상" or roi_moderate < 5 or has_assumed_risk:
        return "비추천", "위험도가 높거나 수익률이 낮습니다."
    elif risk_level == "하" and roi_moderate >= 15:
        return "추천", f"위험도 낮고 예상 수익률 {roi_moderate:.1f}%로 양호합니다."
    else:
        return "보류", "추가 검토가 필요합니다."
```

---

## 5. 에이전트 노드 구현

### 5.1 valuation 노드

> 파일: `backend/app/agents/nodes/valuation.py`

```python
async def valuation_node(state: AgentState) -> AgentState:
    """
    처리 흐름:
    1. 권리분석, 시장데이터, 뉴스분석 결과 수집
    2. 비용 산출 (취득세, 명도비 등)
    3. 입찰 적정가 산출 (3단계)
    4. 매도 적정가 산출 (3단계)
    5. 수익률 분석
    6. 입찰 추천 판단
    7. Claude로 종합 의견 생성
    8. ValuationResult 생성
    """
    rights = state.get("rights_analysis")
    market = state.get("market_data")
    news = state.get("news_analysis")

    # 추정 시세 결정
    if market:
        estimated_value = market.price_range.avg_price * 10000  # 만원 → 원
    else:
        estimated_value = 0

    # 비용 산출
    assumed_cost = rights.total_assumed_amount if rights else 0
    num_tenants = len(rights.tenants) if rights else 0
    has_opposition = any(t.has_opposition_right for t in rights.tenants) if rights else False

    costs = calculate_cost_breakdown(
        bid_price=estimated_value,
        property_type="주택",
        assumed_rights_cost=assumed_cost,
        num_tenants=num_tenants,
        has_opposition_tenants=has_opposition,
    )

    # 적정가 산출
    bid_range = calculate_bid_price_range(estimated_value, assumed_cost, costs.total_cost, 0)
    sale_range = calculate_sale_price_range(
        estimated_value,
        market.price_trend.direction if market else "보합",
        bool(news and news.positive_factors),
        bool(news and news.negative_factors),
    )

    # 수익률
    profitability = calculate_profitability(bid_range.moderate, sale_range, costs.total_cost)

    # 추천 판단
    risk_level = rights.risk_level if rights else "중"
    recommendation, reason = determine_recommendation(
        risk_level, profitability.roi_moderate, assumed_cost > 0,
    )

    # Claude 종합 의견
    summary = await generate_analysis_summary(rights, market, news, recommendation)

    result = ValuationResult(
        recommendation=recommendation,
        recommendation_reason=reason,
        bid_price=bid_range,
        sale_price=sale_range,
        profitability=profitability,
        cost_breakdown=costs,
        overall_risk=RiskAssessment(...),
        analysis_summary=summary,
        confidence_score=0.8,
        disclaimer="본 분석은 AI에 의한 참고용 정보이며, 최종 투자 판단의 책임은 사용자에게 있습니다.",
    )

    return {**state, "valuation": result}
```

---

## 6. 테스트 가이드

### 6.1 테스트 케이스

| ID | 테스트명 | 설명 | 기대 결과 |
|:---:|:---|:---|:---|
| T-1 | `test_acquisition_tax_under_600m` | 6억 이하 취득세 | 1% 적용 |
| T-2 | `test_acquisition_tax_over_900m` | 9억 초과 취득세 | 3% 적용 |
| T-3 | `test_bid_price_range` | 적정가 3단계 | conservative < moderate < aggressive |
| T-4 | `test_roi_positive` | 양의 수익률 | roi > 0 |
| T-5 | `test_recommend_high_roi_low_risk` | 고수익+저위험 | "추천" |
| T-6 | `test_not_recommend_high_risk` | 고위험 | "비추천" |
| T-7 | `test_cost_breakdown_sum` | 비용 합계 | total_cost = 각 항목 합 |

### 6.2 테스트 실행

```bash
cd backend
uv run pytest tests/unit/agents/test_valuation.py -v
```

---

## 파일 변경 요약

### 수정 파일

| 파일 경로 | 변경 내용 |
|:---|:---|
| `backend/app/agents/nodes/valuation.py` | 가치 평가 노드 전체 구현 |

### 신규 생성 파일

| 파일 경로 | 설명 |
|:---|:---|
| `backend/app/agents/tools/cost_calculator.py` | 비용 산출 유틸리티 (취득세, 명도비 등) |
| `backend/app/agents/prompts/valuation_prompts.py` | 가치 평가 LLM 프롬프트 |
| `backend/tests/unit/agents/test_valuation.py` | 단위 테스트 |
