# Feature Specification: 한국 부동산 경매 분석 에이전트

## 1. 프로젝트 개요

### 1.1 요약
LangGraph 기반의 한국 부동산 경매 분석 AI 에이전트이다. 사용자가 경매 사건 정보를 직접 입력하면, 국토부 실거래가 공공데이터 API와 LLM을 활용하여 적정 입찰가 산출, 시세 조회, 단기 매도가 추정, 권리분석 리스크 평가를 수행한다.

### 1.2 해결하려는 문제
- 부동산 경매 초보자가 적정 입찰가를 판단하기 어렵다
- 권리관계 분석에 전문 지식이 필요하나 접근성이 낮다
- 시세 확인, 수익성 분석 등을 여러 사이트에서 개별적으로 수행해야 하는 번거로움이 있다

### 1.3 비즈니스 목표
- 경매 입찰 의사결정에 필요한 핵심 분석을 하나의 채팅 인터페이스에서 제공
- 권리분석 리스크를 체계적으로 평가하여 낙찰 후 위험 최소화
- 실거래가 데이터 기반의 객관적 시세 분석 제공

### 1.4 대상 사용자
- 부동산 경매에 관심 있는 개인 투자자
- 경매 초보자 ~ 중급자
- 법률 전문가가 아닌 일반 사용자

---

## 2. 기술 스택 및 아키텍처

### 2.1 기술 스택

| 구분 | 기술 | 버전/비고 |
|------|------|-----------|
| 언어 | Python | 3.12+ |
| 에이전트 오케스트레이션 | LangGraph | LangChain 생태계 |
| UI | Streamlit | 채팅 인터페이스 |
| LLM | OpenAI GPT / Anthropic Claude | 설정으로 선택 가능 |
| 외부 API | 국토부 실거래가 공공데이터 API | data.go.kr |
| 패키지 관리 | uv / pip | pyproject.toml 기반 |

### 2.2 프로젝트 구조

```
my_auction/
├── main.py                      # Streamlit 앱 엔트리포인트
├── pyproject.toml               # 프로젝트 메타데이터 및 의존성
├── SPEC.md                      # 본 스펙 문서
├── .env.example                 # API 키 설정 템플릿
├── .env                         # 실제 API 키 (gitignore 대상)
├── src/
│   ├── __init__.py
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── graph.py             # LangGraph 워크플로우 정의
│   │   ├── nodes.py             # 각 분석 노드 구현
│   │   └── state.py             # AgentState 타입 정의
│   ├── tools/
│   │   ├── __init__.py
│   │   └── real_estate_api.py   # 국토부 실거래가 API 클라이언트
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py           # Pydantic 데이터 모델
│   └── llm/
│       ├── __init__.py
│       └── provider.py          # LLM 프로바이더 추상화
└── ui/
    └── app.py                   # Streamlit UI 컴포넌트
```

### 2.3 시스템 아키텍처 다이어그램

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit UI (채팅)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────┐  │
│  │ 사건정보 입력  │  │  채팅 메시지   │  │  분석 결과 표시    │  │
│  └──────┬───────┘  └──────┬───────┘  └───────────────────┘  │
└─────────┼─────────────────┼──────────────────────────────────┘
          │                 │
          v                 v
┌─────────────────────────────────────────────────────────────┐
│                LangGraph Agent (graph.py)                     │
│                                                               │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌────────┐ │
│  │ 입력파싱   │───>│ 라우터    │───>│ 분석노드   │───>│ 종합    │ │
│  │  노드     │    │  노드    │    │ (병렬)    │    │ 노드   │ │
│  └──────────┘    └──────────┘    └──────────┘    └────────┘ │
│                       │               │                      │
│                       v               v                      │
│              ┌──────────────┐  ┌──────────────┐             │
│              │  시세조회     │  │  권리분석     │             │
│              │  입찰가산출   │  │  매도가추정   │             │
│              └──────┬───────┘  └──────────────┘             │
└─────────────────────┼────────────────────────────────────────┘
                      │
                      v
┌─────────────────────────────────┐   ┌──────────────────────┐
│  국토부 실거래가 API (data.go.kr) │   │  LLM Provider        │
│  - 아파트 실거래가               │   │  - OpenAI GPT         │
│  - 연립다세대 실거래가            │   │  - Anthropic Claude   │
│  - 단독/다가구 실거래가           │   └──────────────────────┘
└─────────────────────────────────┘
```

### 2.4 의존성 패키지

```toml
[project]
dependencies = [
    "langgraph>=0.2.0",
    "langchain>=0.3.0",
    "langchain-openai>=0.2.0",
    "langchain-anthropic>=0.2.0",
    "streamlit>=1.38.0",
    "pydantic>=2.0.0",
    "httpx>=0.27.0",
    "python-dotenv>=1.0.0",
]
```

---

## 3. LangGraph 워크플로우 설계

### 3.1 AgentState 정의

```python
# src/agent/state.py
from typing import TypedDict, Annotated, Literal
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage

class AuctionCase(TypedDict):
    """사용자가 입력한 경매 사건 정보"""
    case_number: str              # 사건번호 (예: 2024타경12345)
    court: str                    # 관할법원
    property_type: str            # 물건종류 (아파트/연립/단독/토지 등)
    address: str                  # 소재지 주소
    area_m2: float                # 전용면적 (m2)
    appraisal_value: int          # 감정가 (원)
    minimum_bid: int              # 최저매각가격 (원)
    bid_count: int                # 유찰 횟수
    rights: list[dict]            # 권리관계 목록

class RightEntry(TypedDict):
    """개별 권리관계 정보"""
    type: str                     # 유형: 근저당권, 가압류, 전세권, 임차인 등
    creditor: str                 # 권리자/채권자
    amount: int                   # 채권액/보증금 (원)
    date: str                     # 설정일/전입일
    is_senior: bool               # 선순위 여부 (매각기일 기준)
    note: str                     # 비고 (대항력 여부, 배당 가능성 등)

class MarketData(TypedDict):
    """시세/거래 데이터"""
    recent_transactions: list[dict]   # 최근 거래 내역
    avg_price_per_m2: int             # 평당 평균 시세
    transaction_volume: int           # 거래량
    price_trend: str                  # 시세 추이 (상승/보합/하락)
    data_period: str                  # 데이터 조회 기간

class AnalysisResult(TypedDict):
    """종합 분석 결과"""
    recommended_bid_range: dict       # 추천 입찰가 범위 {min, max, optimal}
    market_analysis: dict             # 시세 분석 결과
    short_term_sale_estimate: dict    # 단기 매도가 추정
    risk_assessment: dict             # 권리분석 리스크 평가
    overall_opinion: str              # 종합 의견

class AgentState(TypedDict):
    """LangGraph 에이전트 전체 상태"""
    messages: Annotated[list[BaseMessage], add_messages]
    auction_case: AuctionCase | None
    market_data: MarketData | None
    analysis_result: AnalysisResult | None
    current_step: str
    error: str | None
```

### 3.2 워크플로우 노드

#### 노드 목록

| 노드 이름 | 역할 | 입력 | 출력 |
|-----------|------|------|------|
| `parse_input` | 사용자 입력 파싱 및 구조화 | 사용자 메시지 | `AuctionCase` |
| `router` | 분석 유형 라우팅 | `AuctionCase`, 사용자 요청 | 분기 결정 |
| `fetch_market_data` | 국토부 API로 시세 조회 | 소재지 주소, 물건종류 | `MarketData` |
| `analyze_bid_price` | 적정 입찰가 산출 | `AuctionCase`, `MarketData` | 입찰가 범위 |
| `analyze_rights` | 권리관계 리스크 분석 | `AuctionCase.rights` | 리스크 등급 및 상세 |
| `estimate_sale_price` | 단기 매도가 추정 | `MarketData`, `AuctionCase` | 매도가 추정 |
| `synthesize` | 분석 결과 종합 | 모든 분석 결과 | `AnalysisResult` |
| `respond` | 최종 응답 생성 | `AnalysisResult` | 사용자 응답 메시지 |

#### 노드 상세 설명

**3.2.1 parse_input 노드**

사용자의 자연어 입력 또는 구조화된 폼 입력을 `AuctionCase` 객체로 변환한다.

- LLM을 사용하여 자연어에서 구조화된 데이터 추출
- 필수 필드 누락 시 추가 입력 요청 메시지 생성
- 필수 필드: `address`, `appraisal_value`, `minimum_bid`
- 선택 필드: `case_number`, `court`, `area_m2`, `bid_count`, `rights`

```python
async def parse_input(state: AgentState) -> AgentState:
    """사용자 입력을 파싱하여 AuctionCase로 변환"""
    last_message = state["messages"][-1]

    # LLM으로 구조화된 데이터 추출
    auction_case = await llm.extract_structured(
        last_message.content,
        schema=AuctionCase
    )

    # 필수 필드 검증
    missing = validate_required_fields(auction_case)
    if missing:
        return {
            **state,
            "messages": [AIMessage(content=f"다음 정보가 필요합니다: {missing}")]
        }

    return {**state, "auction_case": auction_case, "current_step": "parsed"}
```

**3.2.2 router 노드**

사용자의 요청 의도를 파악하여 필요한 분석 노드로 라우팅한다.

라우팅 조건:
- `"all"` -- 전체 분석 (기본값): 모든 분석 노드 실행
- `"market_only"` -- 시세 조회만 요청한 경우
- `"rights_only"` -- 권리분석만 요청한 경우
- `"bid_only"` -- 입찰가 산출만 요청한 경우 (시세 조회 선행 필요)
- `"need_more_info"` -- 정보 부족으로 추가 입력 필요

```python
def router(state: AgentState) -> str:
    """분석 유형을 결정하여 라우팅"""
    if state.get("error"):
        return "need_more_info"
    if not state.get("auction_case"):
        return "need_more_info"

    # LLM으로 사용자 의도 파악하거나, 기본값 all
    intent = classify_intent(state["messages"])
    return intent  # "all" | "market_only" | "rights_only" | "bid_only" | "need_more_info"
```

**3.2.3 fetch_market_data 노드**

국토부 실거래가 API를 호출하여 해당 지역의 시세 및 거래량 데이터를 조회한다.

- 주소에서 법정동코드 추출
- 물건종류에 따라 적절한 API 엔드포인트 선택
- 최근 6개월 ~ 1년간 거래 데이터 조회
- API 호출 실패 시 에러 상태 설정 후 계속 진행 (시세 데이터 없이 분석)

**3.2.4 analyze_bid_price 노드**

적정 입찰가 범위를 산출한다.

산출 로직:
1. 시세 기반 가치 평가: `avg_price_per_m2 * area_m2`
2. 감정가 대비 시세 비율 산출
3. 유찰 횟수에 따른 최저가 할인율 반영
4. 권리분석 리스크 가중치 적용
5. 최종 입찰가 범위 산출: `{min, max, optimal}`

```
추천 입찰가 범위 산출 공식:

시세_추정가 = 평당_시세 * 전용면적
시세_대비_감정가_비율 = 감정가 / 시세_추정가

# 기본 입찰가 (시세의 70~85% 범위가 일반적)
기본_입찰_하한 = 시세_추정가 * 0.70
기본_입찰_상한 = 시세_추정가 * 0.85

# 리스크 반영 조정
리스크_할인율 = risk_grade에 따라 0% ~ 15%
최종_하한 = 기본_입찰_하한 * (1 - 리스크_할인율)
최종_상한 = 기본_입찰_상한 * (1 - 리스크_할인율)

# 최저매각가 대비 검증
최종_하한 = max(최종_하한, 최저매각가격)
```

LLM은 이 수치 계산 결과를 바탕으로 시장 상황, 물건 특성 등을 고려한 정성적 의견을 추가한다.

**3.2.5 analyze_rights 노드**

사용자가 입력한 권리관계 정보를 분석하여 리스크 등급을 산출한다.

리스크 등급 체계:

| 등급 | 설명 | 조건 |
|------|------|------|
| A (안전) | 인수할 권리 없음, 말소기준권리 이후 설정만 존재 | 모든 권리가 매각으로 소멸 |
| B (주의) | 소액 인수 권리 존재 가능 | 소액임차인 존재, 인수 금액 소규모 |
| C (위험) | 상당한 인수 권리 존재 | 선순위 전세권, 대항력 있는 임차인 등 |
| D (고위험) | 대규모 인수 권리 또는 복잡한 권리관계 | 유치권, 법정지상권, 대규모 선순위 채권 등 |

분석 항목:
- 말소기준권리 판단 (최선순위 근저당/압류/가압류/담보가등기)
- 선순위/후순위 권리 분류
- 대항력 있는 임차인 판단 (전입신고 + 확정일자 기준)
- 인수해야 할 권리 총액 산출
- 배당 시뮬레이션 (간이)

LLM은 권리관계 데이터를 기반으로 법적 해석과 실무적 조언을 생성한다.

**3.2.6 estimate_sale_price 노드**

낙찰 후 단기(6개월 이내) 매도 시 예상 매도가를 추정한다.

추정 로직:
1. 현재 시세 기반 매도 가능가: `시세 * 0.90~0.95` (급매 할인)
2. 취득세, 등록비, 명도비용 등 부대비용 산출
3. 양도소득세 고려 (단기 보유 높은 세율)
4. 순수익률 계산

```
예상_매도가 = 시세_추정가 * 단기_매도_할인율(0.90~0.95)

부대비용:
  - 취득세: 낙찰가 * 취득세율 (주택 1~3%, 용도별 상이)
  - 등록비용: 약 낙찰가 * 0.2%
  - 명도비용: 0 ~ 500만원 (임차인 유무에 따라)
  - 기타: 이사비 보조, 수리비 등

순수익 = 예상_매도가 - 낙찰가 - 부대비용 - 양도세_추정
수익률 = 순수익 / (낙찰가 + 부대비용) * 100
```

**3.2.7 synthesize 노드**

모든 분석 결과를 종합하여 `AnalysisResult`를 구성한다.

**3.2.8 respond 노드**

`AnalysisResult`를 사용자 친화적인 자연어 응답으로 변환한다. LLM을 사용하여 분석 결과를 설명하고 투자 의견을 제시한다.

### 3.3 워크플로우 그래프 (엣지 정의)

```python
# src/agent/graph.py
from langgraph.graph import StateGraph, END

def build_graph():
    workflow = StateGraph(AgentState)

    # 노드 등록
    workflow.add_node("parse_input", parse_input)
    workflow.add_node("router", router_node)
    workflow.add_node("fetch_market_data", fetch_market_data)
    workflow.add_node("analyze_bid_price", analyze_bid_price)
    workflow.add_node("analyze_rights", analyze_rights)
    workflow.add_node("estimate_sale_price", estimate_sale_price)
    workflow.add_node("synthesize", synthesize)
    workflow.add_node("respond", respond)

    # 엣지 정의
    workflow.set_entry_point("parse_input")
    workflow.add_edge("parse_input", "router")

    # 조건부 라우팅
    workflow.add_conditional_edges(
        "router",
        route_decision,
        {
            "all": "fetch_market_data",
            "market_only": "fetch_market_data",
            "rights_only": "analyze_rights",
            "bid_only": "fetch_market_data",
            "need_more_info": "respond",
        }
    )

    # 시세 조회 이후 분기
    workflow.add_conditional_edges(
        "fetch_market_data",
        post_market_route,
        {
            "all": "analyze_bid_price",      # 전체 분석 흐름
            "market_only": "respond",         # 시세만 응답
            "bid_only": "analyze_bid_price",  # 입찰가 산출로
        }
    )

    # 입찰가 분석 후 -> 권리분석 (all인 경우) 또는 종합
    workflow.add_conditional_edges(
        "analyze_bid_price",
        post_bid_route,
        {
            "all": "analyze_rights",
            "bid_only": "synthesize",
        }
    )

    # 권리분석 후 -> 매도가 추정 (all인 경우) 또는 종합
    workflow.add_conditional_edges(
        "analyze_rights",
        post_rights_route,
        {
            "all": "estimate_sale_price",
            "rights_only": "respond",
        }
    )

    # 매도가 추정 후 -> 종합
    workflow.add_edge("estimate_sale_price", "synthesize")

    # 종합 -> 응답
    workflow.add_edge("synthesize", "respond")

    # 응답 -> 종료
    workflow.add_edge("respond", END)

    return workflow.compile()
```

### 3.4 워크플로우 흐름도 (전체 분석 기준)

```
           ┌────────────┐
           │ parse_input │
           └──────┬─────┘
                  v
           ┌────────────┐
           │   router    │
           └──────┬─────┘
                  │
      ┌───────┬──┴──┬────────┬───────────┐
      v       v     v        v           v
  [all]  [market] [bid]  [rights]  [need_more_info]
      │       │     │        │           │
      v       │     v        v           v
 ┌──────────┐ │ ┌──────────┐ │      ┌─────────┐
 │fetch_    │ │ │fetch_    │ │      │ respond │
 │market_   │ │ │market_   │ │      │(추가입력│
 │data      │ │ │data      │ │      │ 요청)   │
 └────┬─────┘ │ └────┬─────┘ │      └─────────┘
      v       │      v       │
 ┌──────────┐ │ ┌──────────┐ │
 │analyze_  │ │ │analyze_  │ │
 │bid_price │ │ │bid_price │ │
 └────┬─────┘ │ └────┬─────┘ │
      v       │      v       │
 ┌──────────┐ │ ┌──────────┐ │
 │analyze_  │ │ │synthesize│ │
 │rights    │ │ └────┬─────┘ │
 └────┬─────┘ │      v       v
      v       │ ┌─────────┐  ┌─────────┐
 ┌──────────┐ │ │ respond │  │ respond │
 │estimate_ │ │ └─────────┘  └─────────┘
 │sale_price│ │
 └────┬─────┘ │
      v       │
 ┌──────────┐ │
 │synthesize│ │
 └────┬─────┘ │
      v       v
 ┌─────────┐ ┌─────────┐
 │ respond │ │ respond │
 └─────────┘ └─────────┘
```

---

## 4. 각 기능별 상세 스펙

### 4.1 예상 적절 입찰가 산출

**기능 ID**: F-001

**설명**: 감정가, 최저가, 시세, 권리분석 결과를 종합하여 적정 입찰가 범위를 제시한다.

**입력 데이터**:
- 감정가 (필수)
- 최저매각가격 (필수)
- 소재지 주소 (필수, 시세 조회용)
- 전용면적 (권장)
- 유찰 횟수 (선택)
- 권리관계 (선택, 리스크 가중치 반영)

**출력 데이터**:
```json
{
  "recommended_bid_range": {
    "min": 180000000,
    "max": 220000000,
    "optimal": 200000000
  },
  "appraisal_ratio": 0.75,
  "market_ratio": 0.82,
  "risk_discount_applied": 0.05,
  "reasoning": "해당 물건의 시세 대비 감정가가 적절하며..."
}
```

**비즈니스 규칙**:
- 추천 입찰가는 항상 최저매각가격 이상이어야 한다
- 추천 입찰가는 감정가의 120%를 초과하지 않도록 경고한다
- 시세 데이터가 없는 경우 감정가 기반으로만 산출하되, 정확도 제한을 고지한다
- 권리분석 리스크가 D등급인 경우 입찰 자체에 대한 경고를 함께 표시한다

### 4.2 물건지 최근 거래량/시세 확인

**기능 ID**: F-002

**설명**: 국토부 실거래가 API를 통해 해당 지역의 최근 거래 데이터를 조회하여 시세를 파악한다.

**입력 데이터**:
- 소재지 주소 (필수)
- 물건종류 (필수: 아파트/연립다세대/단독다가구)
- 전용면적 (선택, 유사 면적 필터링용)

**출력 데이터**:
```json
{
  "recent_transactions": [
    {
      "deal_date": "2024-11",
      "deal_amount": 320000000,
      "area_m2": 84.5,
      "floor": 12,
      "address_detail": "XX아파트 101동"
    }
  ],
  "avg_price_per_m2": 3800000,
  "transaction_volume_6m": 45,
  "price_trend": "보합",
  "price_trend_detail": "최근 6개월간 -1.2% 소폭 하락 추세"
}
```

**비즈니스 규칙**:
- 조회 기간: 기본 최근 6개월, 데이터 부족 시 12개월까지 확대
- 유사 면적 필터: 입력 면적 기준 +/-10% 범위 우선 조회
- 거래 데이터 0건인 경우: 인접 동/구 단위로 확대 검색 시도
- 시세 추이: 3개월 전 대비 현재 평균가 비교

### 4.3 단기 매도시 가능한 매도가 추정

**기능 ID**: F-003

**설명**: 낙찰 후 6개월 이내 매도를 가정하여 예상 매도가와 수익률을 분석한다.

**입력 데이터**:
- 시세 데이터 (F-002 결과)
- 입찰 예정가 또는 추천 입찰가 (F-001 결과)
- 물건종류
- 권리관계 (명도 비용 산출용)

**출력 데이터**:
```json
{
  "estimated_sale_price": {
    "optimistic": 310000000,
    "realistic": 295000000,
    "conservative": 280000000
  },
  "costs": {
    "acquisition_tax": 6000000,
    "registration_fee": 400000,
    "eviction_cost": 3000000,
    "repair_estimate": 5000000,
    "agent_fee": 2000000,
    "capital_gains_tax_estimate": 8000000
  },
  "profit_analysis": {
    "gross_profit": 95000000,
    "net_profit": 70600000,
    "roi_percent": 35.3
  }
}
```

**비즈니스 규칙**:
- 단기 매도 할인율: 시세 대비 5~10% 할인 적용
- 취득세율: 주택 유형 및 보유 주택 수에 따라 1~12% (기본 1주택 1~3% 적용, 사용자에게 다주택 여부 확인)
- 양도소득세: 단기 보유(1년 미만) 70%, 1~2년 60% 세율 기본 적용
- 수리비: 별도 입력 없으면 기본 500만원 가정
- 명도비: 임차인 유무에 따라 0~500만원
- 면책 고지: "본 분석은 참고용이며, 실제 세금 및 비용은 전문가 상담을 권합니다"

### 4.4 권리분석 리스크 평가

**기능 ID**: F-004

**설명**: 사용자가 입력한 권리관계 정보를 분석하여 리스크 등급과 상세 분석 결과를 제시한다.

**입력 데이터**:
- 권리관계 목록 (유형, 권리자, 금액, 설정일, 선순위 여부 등)
- 매각기일 기준일 (선택)

**출력 데이터**:
```json
{
  "risk_grade": "B",
  "risk_grade_label": "주의",
  "summary": "소액임차인 1명이 존재하여 보증금 일부 인수 가능성 있음",
  "total_assumed_amount": 15000000,
  "details": [
    {
      "right_type": "근저당권",
      "analysis": "말소기준권리. 매각으로 소멸됨.",
      "risk": "없음",
      "assumed_amount": 0
    },
    {
      "right_type": "임차인",
      "analysis": "전입신고 2023.01.15, 확정일자 2023.01.20. 소액임차인 해당 여부 확인 필요.",
      "risk": "보증금 일부 인수 가능",
      "assumed_amount": 15000000
    }
  ],
  "recommendations": [
    "임차인의 실제 거주 여부 현장 확인 필요",
    "배당요구종기일 내 배당신청 여부 확인 권장"
  ]
}
```

**비즈니스 규칙**:
- 말소기준권리 자동 판단: 최선순위 (근)저당권, (가)압류, 담보가등기 중 가장 먼저 설정된 것
- 소액임차인 판단: 지역별 소액보증금 기준 적용 (수도권/광역시/기타)
- 대항력 판단: 전입신고일이 말소기준권리 설정일보다 앞서는 경우
- 유치권, 법정지상권 등 특수 권리는 D등급 자동 부여
- 면책 고지: "본 분석은 AI 기반 참고 자료이며, 정확한 권리분석은 법무사 또는 변호사 상담을 권합니다"

---

## 5. 데이터 모델

### 5.1 Pydantic 스키마 정의

```python
# src/models/schemas.py
from pydantic import BaseModel, Field
from enum import Enum
from datetime import date

class PropertyType(str, Enum):
    APARTMENT = "아파트"
    VILLA = "연립다세대"
    HOUSE = "단독다가구"
    OFFICETEL = "오피스텔"
    COMMERCIAL = "상가"
    LAND = "토지"

class RiskGrade(str, Enum):
    A = "A"  # 안전
    B = "B"  # 주의
    C = "C"  # 위험
    D = "D"  # 고위험

class RightType(str, Enum):
    MORTGAGE = "근저당권"
    SEIZURE = "압류"
    PROVISIONAL_SEIZURE = "가압류"
    SECURITY_DEPOSIT = "전세권"
    TENANT = "임차인"
    LIEN = "유치권"
    SUPERFICIES = "법정지상권"
    PROVISIONAL_REGISTRATION = "가등기"
    OTHER = "기타"

class RightEntry(BaseModel):
    """개별 권리관계"""
    type: RightType
    creditor: str = Field(description="권리자/채권자명")
    amount: int = Field(ge=0, description="채권액 또는 보증금 (원)")
    date: str = Field(description="설정일 또는 전입일 (YYYY-MM-DD)")
    is_senior: bool = Field(default=False, description="말소기준권리 대비 선순위 여부")
    note: str = Field(default="", description="비고")

class AuctionCaseInput(BaseModel):
    """사용자 입력: 경매 사건 정보"""
    case_number: str | None = Field(default=None, description="사건번호")
    court: str | None = Field(default=None, description="관할법원")
    property_type: PropertyType = Field(description="물건종류")
    address: str = Field(description="소재지 전체 주소")
    area_m2: float | None = Field(default=None, ge=0, description="전용면적 (m2)")
    appraisal_value: int = Field(gt=0, description="감정가 (원)")
    minimum_bid: int = Field(gt=0, description="최저매각가격 (원)")
    bid_count: int = Field(default=0, ge=0, description="유찰 횟수")
    rights: list[RightEntry] = Field(default_factory=list, description="권리관계 목록")

class TransactionRecord(BaseModel):
    """실거래 내역"""
    deal_date: str = Field(description="거래 연월 (YYYY-MM)")
    deal_amount: int = Field(description="거래금액 (원)")
    area_m2: float = Field(description="전용면적 (m2)")
    floor: int | None = Field(default=None, description="층")
    building_name: str | None = Field(default=None, description="건물명")

class MarketDataResponse(BaseModel):
    """시세 조회 결과"""
    recent_transactions: list[TransactionRecord]
    avg_price_per_m2: int = Field(description="m2당 평균 시세 (원)")
    transaction_volume: int = Field(description="조회 기간 내 거래 건수")
    price_trend: str = Field(description="시세 추이 (상승/보합/하락)")
    price_trend_detail: str = Field(description="시세 추이 상세 설명")
    data_period: str = Field(description="데이터 조회 기간")

class BidRecommendation(BaseModel):
    """입찰가 추천 결과"""
    min_bid: int = Field(description="추천 최저 입찰가")
    max_bid: int = Field(description="추천 최고 입찰가")
    optimal_bid: int = Field(description="최적 입찰가")
    appraisal_ratio: float = Field(description="감정가 대비 비율")
    market_ratio: float = Field(description="시세 대비 비율")
    reasoning: str = Field(description="산출 근거 설명")

class CostBreakdown(BaseModel):
    """비용 내역"""
    acquisition_tax: int = Field(description="취득세")
    registration_fee: int = Field(description="등기비용")
    eviction_cost: int = Field(default=0, description="명도비용")
    repair_estimate: int = Field(default=5000000, description="수리비 추정")
    agent_fee: int = Field(default=0, description="중개수수료")
    capital_gains_tax_estimate: int = Field(default=0, description="양도세 추정")

class SalePriceEstimate(BaseModel):
    """매도가 추정 결과"""
    optimistic: int = Field(description="낙관적 매도가")
    realistic: int = Field(description="현실적 매도가")
    conservative: int = Field(description="보수적 매도가")
    costs: CostBreakdown
    net_profit_estimate: int = Field(description="순수익 추정 (현실적 기준)")
    roi_percent: float = Field(description="수익률 (%)")

class RightAnalysisDetail(BaseModel):
    """개별 권리 분석 결과"""
    right_type: str
    analysis: str
    risk_level: str
    assumed_amount: int = Field(description="인수해야 할 금액")

class RightsAssessment(BaseModel):
    """권리분석 종합 결과"""
    risk_grade: RiskGrade
    risk_grade_label: str
    summary: str
    total_assumed_amount: int
    details: list[RightAnalysisDetail]
    recommendations: list[str]

class FullAnalysisResult(BaseModel):
    """전체 분석 종합 결과"""
    auction_case: AuctionCaseInput
    market_data: MarketDataResponse | None
    bid_recommendation: BidRecommendation | None
    sale_estimate: SalePriceEstimate | None
    rights_assessment: RightsAssessment | None
    overall_opinion: str = Field(description="AI 종합 의견")
    disclaimers: list[str] = Field(description="면책 고지 목록")
```

---

## 6. UI 화면 설계

### 6.1 전체 레이아웃

Streamlit 기반 단일 페이지 채팅 인터페이스로 구성한다.

```
┌──────────────────────────────────────────────────────────┐
│  [로고] 부동산 경매 분석 AI 에이전트          [설정]       │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌─ 사이드바 ──────────────┐  ┌─ 메인 영역 ───────────┐  │
│  │                        │  │                        │  │
│  │ [경매사건 정보 입력 폼]  │  │  [채팅 메시지 영역]     │  │
│  │                        │  │                        │  │
│  │ - 소재지 주소           │  │  사용자: 분석해주세요   │  │
│  │ - 물건종류 (드롭다운)    │  │                        │  │
│  │ - 감정가               │  │  AI: 분석 결과를        │  │
│  │ - 최저매각가격          │  │      알려드리겠습니다.   │  │
│  │ - 전용면적             │  │                        │  │
│  │ - 유찰횟수             │  │  [시세 차트]            │  │
│  │                        │  │  [리스크 표]            │  │
│  │ [권리관계 입력]         │  │  [입찰가 범위]          │  │
│  │ + 권리 추가 버튼        │  │                        │  │
│  │                        │  │                        │  │
│  │ [분석 시작] 버튼        │  │                        │  │
│  │                        │  ├────────────────────────┤  │
│  │ ─────────────────      │  │ [메시지 입력창]         │  │
│  │ [설정]                 │  │ [전송] 버튼             │  │
│  │ - LLM 선택             │  └────────────────────────┘  │
│  │   (OpenAI/Claude)      │                              │
│  │ - 분석 상세도           │                              │
│  └────────────────────────┘                              │
└──────────────────────────────────────────────────────────┘
```

### 6.2 사이드바: 경매사건 정보 입력 폼

**구성 요소**:

| 필드 | 위젯 | 필수여부 | 기본값 |
|------|------|---------|--------|
| 소재지 주소 | text_input | 필수 | - |
| 물건종류 | selectbox | 필수 | 아파트 |
| 감정가 | number_input | 필수 | - |
| 최저매각가격 | number_input | 필수 | - |
| 전용면적(m2) | number_input | 선택 | - |
| 사건번호 | text_input | 선택 | - |
| 관할법원 | text_input | 선택 | - |
| 유찰횟수 | number_input | 선택 | 0 |

**권리관계 입력 영역**:
- "권리 추가" 버튼 클릭 시 동적으로 입력 행 추가
- 각 행: 유형(selectbox) / 권리자(text) / 금액(number) / 설정일(date) / 선순위여부(checkbox)
- 행 삭제 버튼 제공

### 6.3 메인 영역: 채팅 인터페이스

- `st.chat_message`를 사용한 대화형 UI
- 사용자 메시지와 AI 응답을 구분하여 표시
- 분석 결과는 구조화된 형태로 표시:
  - 시세 데이터: `st.dataframe` 또는 `st.table`로 거래 내역 표시
  - 시세 추이: `st.line_chart`로 그래프 표시
  - 리스크 등급: 색상 코드 적용 (`st.metric` 활용)
  - 입찰가 범위: `st.metric` 3개 (최저/최적/최고)
  - 수익 분석: `st.table`로 비용 내역 표시

### 6.4 설정 패널

- LLM 프로바이더 선택: `st.radio` (OpenAI / Anthropic Claude)
- 모델 선택: 프로바이더에 따라 동적으로 모델 목록 표시
- 분석 상세도: `st.slider` (간략 / 보통 / 상세)

### 6.5 Streamlit 세션 상태 관리

```python
# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []
if "auction_case" not in st.session_state:
    st.session_state.auction_case = None
if "analysis_result" not in st.session_state:
    st.session_state.analysis_result = None
```

---

## 7. 국토부 실거래가 API 연동 스펙

### 7.1 사용 API 목록

국토교통부 실거래가 공개시스템 (data.go.kr) API를 사용한다.

| API명 | 서비스ID | 용도 |
|--------|----------|------|
| 아파트매매 실거래 상세 자료 | `getRTMSDataSvcAptTradeDev` | 아파트 실거래가 조회 |
| 연립다세대 매매 실거래자료 | `getRTMSDataSvcRHTrade` | 연립/다세대 실거래가 조회 |
| 단독/다가구 매매 실거래자료 | `getRTMSDataSvcSHTrade` | 단독/다가구 실거래가 조회 |
| 오피스텔 매매 실거래자료 | `getRTMSDataSvcOffiTrade` | 오피스텔 실거래가 조회 |

### 7.2 공통 요청 파라미터

| 파라미터 | 타입 | 필수 | 설명 |
|----------|------|------|------|
| `serviceKey` | string | Y | 공공데이터포털 인증키 |
| `LAWD_CD` | string | Y | 법정동코드 앞 5자리 |
| `DEAL_YMD` | string | Y | 계약년월 (YYYYMM) |
| `pageNo` | int | N | 페이지 번호 (기본 1) |
| `numOfRows` | int | N | 한 페이지 결과 수 (기본 10) |

### 7.3 API 클라이언트 설계

```python
# src/tools/real_estate_api.py
import httpx
from typing import Optional

class RealEstateAPIClient:
    """국토부 실거래가 API 클라이언트"""

    BASE_URL = "http://openapi.molit.go.kr"

    ENDPOINTS = {
        "아파트": "/OpenAPI_ToolInstall498/service/rest/RTMSDataSvcAptTradeDev/getRTMSDataSvcAptTradeDev",
        "연립다세대": "/OpenAPI_ToolInstall498/service/rest/RTMSDataSvcRHTrade/getRTMSDataSvcRHTrade",
        "단독다가구": "/OpenAPI_ToolInstall498/service/rest/RTMSDataSvcSHTrade/getRTMSDataSvcSHTrade",
        "오피스텔": "/OpenAPI_ToolInstall498/service/rest/RTMSDataSvcOffiTrade/getRTMSDataSvcOffiTrade",
    }

    def __init__(self, service_key: str):
        self.service_key = service_key
        self.client = httpx.AsyncClient(timeout=30.0)

    async def get_transactions(
        self,
        property_type: str,
        lawd_cd: str,
        deal_ymd: str,
        page_no: int = 1,
        num_of_rows: int = 100,
    ) -> dict:
        """실거래 데이터 조회"""
        ...

    async def get_recent_transactions(
        self,
        property_type: str,
        lawd_cd: str,
        months: int = 6,
    ) -> list[dict]:
        """최근 N개월 거래 데이터 일괄 조회"""
        ...

    def close(self):
        """클라이언트 종료"""
        ...
```

### 7.4 법정동코드 변환

사용자가 입력한 주소에서 법정동코드(LAWD_CD)를 추출해야 한다.

방법:
1. 행정표준코드관리시스템의 법정동코드 전체 목록 CSV를 로컬에 포함 (약 5만건, 약 2MB)
2. 주소 문자열에서 시/도, 시/군/구, 읍/면/동을 파싱
3. 파싱 결과로 법정동코드 매핑 테이블에서 코드 조회
4. LLM을 활용한 주소 정규화 (불완전한 주소 보정)

```python
# 법정동코드 매핑 예시
# data/lawd_cd.csv (프로젝트에 포함)
# 코드,시도,시군구,읍면동
# 11110,서울특별시,종로구,
# 11110,서울특별시,종로구,청운효자동
# ...

class LawdCodeMapper:
    """법정동코드 매핑"""

    def __init__(self, csv_path: str = "data/lawd_cd.csv"):
        self.mapping = self._load_mapping(csv_path)

    def get_code(self, address: str) -> str | None:
        """주소에서 법정동코드 5자리 추출"""
        ...

    def _parse_address(self, address: str) -> tuple[str, str, str]:
        """주소를 시도/시군구/동 으로 파싱"""
        ...
```

### 7.5 API 응답 처리

- 응답 형식: XML (기본) -- JSON 변환 처리 필요
- 응답 코드 처리:
  - `00`: 정상
  - `01`: 어플리케이션 에러
  - `02`: DB 에러
  - `03`: 데이터 없음
  - `04`: HTTP 에러
  - `05`: 서비스 연결 실패
  - `10`: 잘못된 요청 파라미터
  - `22`: 서비스키 만료
  - `31`: 호출건수 초과
- Rate Limit: 일일 1,000건 (일반 인증키 기준), 초과 시 다음 날까지 대기 필요

### 7.6 데이터 디렉토리

```
my_auction/
├── data/
│   └── lawd_cd.csv        # 법정동코드 매핑 테이블
```

---

## 8. LLM 프로바이더 설계

### 8.1 프로바이더 추상화

```python
# src/llm/provider.py
from abc import ABC, abstractmethod
from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from langchain_anthropic import ChatAnthropic

class LLMProvider(ABC):
    """LLM 프로바이더 추상 클래스"""

    @abstractmethod
    def get_chat_model(self) -> BaseChatModel:
        """LangChain 호환 채팅 모델 반환"""
        ...

    @abstractmethod
    def get_model_name(self) -> str:
        """현재 사용 중인 모델명 반환"""
        ...

class OpenAIProvider(LLMProvider):
    """OpenAI GPT 프로바이더"""

    SUPPORTED_MODELS = [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
    ]

    def __init__(self, api_key: str, model: str = "gpt-4o"):
        self.api_key = api_key
        self.model = model

    def get_chat_model(self) -> ChatOpenAI:
        return ChatOpenAI(
            api_key=self.api_key,
            model=self.model,
            temperature=0.1,
        )

    def get_model_name(self) -> str:
        return f"OpenAI {self.model}"

class AnthropicProvider(LLMProvider):
    """Anthropic Claude 프로바이더"""

    SUPPORTED_MODELS = [
        "claude-sonnet-4-20250514",
        "claude-haiku-35-20241022",
    ]

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514"):
        self.api_key = api_key
        self.model = model

    def get_chat_model(self) -> ChatAnthropic:
        return ChatAnthropic(
            api_key=self.api_key,
            model=self.model,
            temperature=0.1,
        )

    def get_model_name(self) -> str:
        return f"Anthropic {self.model}"

def create_provider(
    provider_type: str,
    api_key: str,
    model: str | None = None,
) -> LLMProvider:
    """팩토리 함수: 설정에 따라 프로바이더 생성"""
    if provider_type == "openai":
        return OpenAIProvider(api_key, model or "gpt-4o")
    elif provider_type == "anthropic":
        return AnthropicProvider(api_key, model or "claude-sonnet-4-20250514")
    else:
        raise ValueError(f"지원하지 않는 프로바이더: {provider_type}")
```

### 8.2 환경 변수 설정

```bash
# .env.example

# LLM 설정
LLM_PROVIDER=openai          # openai 또는 anthropic
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
LLM_MODEL=                    # 비어있으면 프로바이더 기본 모델 사용

# 국토부 실거래가 API
DATA_GO_KR_API_KEY=...        # data.go.kr 인증키
```

### 8.3 LLM 사용 용도별 프롬프트 전략

| 용도 | temperature | 비고 |
|------|-------------|------|
| 사용자 입력 파싱 (Structured Output) | 0.0 | JSON 모드 또는 function calling 활용 |
| 의도 분류 (라우팅) | 0.0 | 분류 작업이므로 결정적 |
| 권리분석 해석 | 0.1 | 법률 지식 기반, 낮은 temperature |
| 종합 의견 생성 | 0.3 | 약간의 창의성 허용 |
| 대화 응답 생성 | 0.3 | 자연스러운 대화 |

---

## 9. 에러 처리 및 제약사항

### 9.1 에러 처리 전략

#### API 에러

| 에러 유형 | 처리 방법 | 사용자 메시지 |
|-----------|-----------|---------------|
| API 키 미설정 | 앱 시작 시 경고 | "API 키가 설정되지 않았습니다. .env 파일을 확인하세요." |
| API 호출 실패 (네트워크) | 3회 재시도 후 실패 처리 | "실거래가 데이터를 가져올 수 없습니다. 네트워크 상태를 확인하세요." |
| API 호출건수 초과 | 호출 중단 + 캐시 데이터 활용 | "오늘 API 호출 한도에 도달했습니다. 캐시된 데이터로 분석합니다." |
| API 데이터 없음 | 조회 기간/범위 확대 시도 | "해당 지역의 최근 거래 데이터가 없습니다. 인근 지역으로 확대 조회합니다." |
| XML 파싱 에러 | 에러 로깅 + graceful degradation | "데이터 처리 중 오류가 발생했습니다." |

#### LLM 에러

| 에러 유형 | 처리 방법 | 사용자 메시지 |
|-----------|-----------|---------------|
| API 키 미설정 | 앱 시작 시 차단 | "LLM API 키가 설정되지 않았습니다." |
| Rate Limit | 지수 백오프 재시도 (최대 3회) | "잠시 후 다시 시도합니다..." |
| 토큰 한도 초과 | 입력 데이터 축소 후 재시도 | "데이터가 너무 많아 일부만 분석합니다." |
| 응답 파싱 실패 | 1회 재시도 + 원본 텍스트 반환 | 구조화되지 않은 텍스트 응답 표시 |

#### 사용자 입력 에러

| 에러 유형 | 처리 방법 |
|-----------|-----------|
| 필수 필드 누락 | 누락 필드를 구체적으로 안내하며 추가 입력 요청 |
| 잘못된 주소 형식 | 법정동코드 매핑 실패 시 올바른 주소 형식 예시 제공 |
| 비현실적 금액 입력 | 경고 표시 (예: 감정가가 100원인 경우) |
| 권리관계 입력 모순 | 모순 사항 지적 후 확인 요청 |

### 9.2 제약사항

1. **데이터 정확성 한계**
   - 국토부 실거래가 데이터는 신고 기반이므로 1~2개월의 시차가 존재한다
   - 아파트 외 물건(연립, 단독)은 거래 데이터가 부족할 수 있다
   - 시세 추정은 인근 유사 거래 기반이므로 개별 물건의 상태(층, 향, 리모델링 등)를 반영하지 못한다

2. **법률 분석 한계**
   - AI 기반 권리분석은 참고 용도이며, 법적 효력이 없다
   - 복잡한 권리관계(다수 이해관계자, 소송 중인 사건 등)의 정확한 분석은 보장하지 않는다
   - 최신 판례나 법률 개정 사항이 반영되지 않을 수 있다

3. **세금 계산 한계**
   - 취득세, 양도소득세 등 세금 추정은 일반적인 세율 기준이며, 개인별 상황(다주택자, 법인 등)에 따라 달라진다
   - 정확한 세금 계산은 세무사 상담이 필요하다

4. **API 호출 제한**
   - data.go.kr 일반 인증키: 일일 1,000건 제한
   - 다수 사용자가 동시에 사용할 경우 호출 한도에 빠르게 도달할 수 있다

5. **크롤링 미사용**
   - 경매 사건 정보는 사용자가 직접 입력해야 하며, 법원경매정보 등 외부 사이트에서 자동 수집하지 않는다

### 9.3 면책 고지문 (앱 하단 상시 표시)

```
[면책 고지]
본 서비스는 AI 기반의 참고용 분석 도구입니다.
- 제공되는 모든 분석 결과는 투자 권유가 아니며, 투자 판단의 책임은 사용자에게 있습니다.
- 권리분석은 법률 전문가의 검토를 대체할 수 없습니다.
- 시세 및 수익률 추정은 실제와 다를 수 있습니다.
- 세금 관련 사항은 세무 전문가와 상담하시기 바랍니다.
```

---

## 부록 A. 용어 정리

| 용어 | 설명 |
|------|------|
| 감정가 | 법원 감정인이 평가한 부동산의 가치 |
| 최저매각가격 | 경매에서 입찰할 수 있는 최저 금액. 유찰 시 20~30% 씩 낮아짐 |
| 유찰 | 입찰자가 없거나 최저매각가격 미달로 매각되지 않은 경우 |
| 말소기준권리 | 매각으로 소멸되는 권리와 인수되는 권리를 구분하는 기준이 되는 권리 |
| 대항력 | 임차인이 제3자(낙찰자)에게 임대차 관계를 주장할 수 있는 법적 힘 |
| 소액임차인 | 보증금이 일정 금액 이하인 임차인으로, 최우선변제권이 인정됨 |
| 법정지상권 | 토지와 건물 소유자가 달라질 때 건물 소유자에게 인정되는 토지 사용권 |
| 유치권 | 타인의 물건을 점유한 자가 채권 변제 시까지 물건을 유치할 수 있는 권리 |
| 배당 | 매각대금을 채권자들에게 순위에 따라 분배하는 절차 |

## 부록 B. 소액임차인 최우선변제금 기준표 (2024년 기준)

| 지역 | 보증금 상한 | 최우선변제금 |
|------|------------|-------------|
| 서울특별시 | 1억 6,500만원 | 5,500만원 |
| 과밀억제권역(서울 제외), 세종, 용인, 화성 | 1억 4,500만원 | 4,800만원 |
| 광역시(과밀억제권역·군 제외), 안산, 김포, 광주, 파주 | 8,000만원 | 2,700만원 |
| 그 밖의 지역 | 6,500만원 | 2,200만원 |

*법률 개정에 따라 변동될 수 있으므로 최신 기준 확인 필요*

---

**문서 작성일**: 2026-02-09
**버전**: 1.0
**상태**: 초안 (Draft)
