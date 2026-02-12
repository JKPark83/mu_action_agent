# PRD-06: AI 에이전트 시스템 (AI Agent System)

> **문서 버전**: v1.0
> **작성일**: 2026-02-12
> **상태**: Draft
> **상위 문서**: PRD-00 시스템 개요

---

## 1. 개요

### 1.1 목적
LangGraph와 DeepAgent를 활용하여 경매 분석 파이프라인을 구성하는 멀티 에이전트 시스템을 설계하고 구현한다.

### 1.2 배경
경매 분석은 문서 파싱, 권리분석, 시장 데이터 수집, 뉴스 분석, 가치 평가 등 여러 단계의 복합적인 작업으로 구성된다. 각 단계를 독립적인 에이전트로 분리하고 LangGraph로 워크플로우를 관리하면, 병렬 처리와 에러 핸들링이 용이해진다.

### 1.3 LangGraph vs DeepAgent 역할 분담

| 구분 | LangGraph | DeepAgent |
|------|-----------|-----------|
| **역할** | 워크플로우 오케스트레이션 | 복잡한 추론/분석 태스크 실행 |
| **강점** | 그래프 기반 상태 관리, 조건부 분기, 병렬 실행 | 자율적 도구 사용, 복잡한 추론 체인 |
| **적용** | 전체 분석 파이프라인 흐름 제어 | 권리분석, 가치평가 등 고수준 추론 |
| **도구** | 상태 그래프, 노드, 엣지, 체크포인트 | Claude Tool Use, 자율 판단 |

---

## 2. 에이전트 아키텍처

### 2.1 전체 워크플로우 (LangGraph State Graph)

```
                    ┌──────────────┐
                    │   START      │
                    │ (PDF 업로드)  │
                    └──────┬───────┘
                           │
                    ┌──────┴───────┐
                    │  문서 파싱    │
                    │  Agent       │
                    └──────┬───────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
       ┌──────┴──────┐ ┌──┴─────┐ ┌───┴──────┐
       │ 권리분석     │ │시장     │ │뉴스      │
       │ Agent       │ │데이터   │ │분석      │
       │(DeepAgent)  │ │Agent   │ │Agent     │
       └──────┬──────┘ └──┬─────┘ └───┬──────┘
              │            │            │
              └────────────┼────────────┘
                           │
                    ┌──────┴───────┐
                    │  가치 평가    │
                    │  Agent       │
                    │ (DeepAgent)  │
                    └──────┬───────┘
                           │
                    ┌──────┴───────┐
                    │  리포트 생성  │
                    │  Agent       │
                    └──────┬───────┘
                           │
                    ┌──────┴───────┐
                    │    END       │
                    │ (결과 반환)   │
                    └──────────────┘
```

### 2.2 병렬 실행 구간
- **병렬 실행**: 권리분석, 시장 데이터 수집, 뉴스 분석은 서로 독립적이므로 병렬 실행
- **순차 실행**: 문서 파싱 → 병렬 분석 → 가치 평가 → 리포트 생성은 순차 실행

---

## 3. 에이전트 상세 설계

### 3.1 문서 파싱 에이전트 (Document Parser Agent)
```python
# LangGraph Node
역할: PDF 문서를 파싱하여 구조화된 데이터로 변환
입력: 업로드된 PDF 파일 목록
출력: 파싱된 문서 데이터 (등기부등본, 매각물건명세서, 감정평가서 등)
도구:
  - pdf_text_extractor: PDF에서 텍스트 추출
  - ocr_processor: 스캔 문서 OCR 처리
  - document_classifier: 문서 유형 분류
  - data_structurer: 비정형 텍스트를 구조화 (Claude 활용)
```

### 3.2 권리분석 에이전트 (Rights Analysis Agent) - DeepAgent
```python
# DeepAgent 활용
역할: 등기부등본 기반 권리관계 분석 및 위험도 평가
입력: 파싱된 등기부등본, 매각물건명세서 데이터
출력: 권리분석 결과 (인수/소멸 권리, 위험도, 임차인 분석)
특성:
  - 복잡한 법률적 판단이 필요하므로 DeepAgent의 자율적 추론 활용
  - Claude Tool Use로 말소기준권리 판단, 대항력 분석 등 수행
  - 불확실한 경우 추가 분석 도구를 자율적으로 호출
도구:
  - rights_analyzer: 권리 인수/소멸 판단
  - tenant_analyzer: 임차인 대항력 분석
  - risk_evaluator: 위험도 평가
```

### 3.3 시장 데이터 에이전트 (Market Data Agent)
```python
# LangGraph Node
역할: 실거래가 및 시세 데이터 수집/분석
입력: 물건 소재지, 면적, 부동산 유형
출력: 시장 데이터 분석 결과 (시세, 트렌드, 전세가율)
도구:
  - molit_api: 국토교통부 실거래가 API 호출
  - address_converter: 주소 → 법정동코드 변환
  - price_analyzer: 가격 통계 분석
  - trend_analyzer: 가격 추이 분석
```

### 3.4 뉴스 분석 에이전트 (News Analysis Agent)
```python
# LangGraph Node
역할: 지역 뉴스 수집 및 호재/악재 분석
입력: 물건 소재지, 지역명
출력: 뉴스 분석 결과 (호재/악재, 지역 매력도)
도구:
  - news_search: 뉴스 검색 API 호출
  - news_classifier: 뉴스 호재/악재 분류 (Claude 활용)
  - news_summarizer: 뉴스 요약 (Claude 활용)
  - trend_synthesizer: 동향 종합 분석
```

### 3.5 가치 평가 에이전트 (Valuation Agent) - DeepAgent
```python
# DeepAgent 활용
역할: 모든 분석 결과를 종합하여 적정가 산출 및 입찰 추천
입력: 권리분석, 시장데이터, 뉴스분석 결과 전체
출력: 최종 가치 평가 결과 (적정가, 수익률, 추천 여부)
특성:
  - 여러 요소를 종합한 복잡한 판단이 필요하므로 DeepAgent 활용
  - 시나리오별 분석을 자율적으로 수행
  - 비용 산출 도구를 자율적으로 호출
도구:
  - cost_calculator: 취득세, 부대비용 계산
  - roi_calculator: 수익률 계산
  - risk_assessor: 종합 위험도 평가
  - recommendation_engine: 입찰 추천 판단
```

### 3.6 리포트 생성 에이전트 (Report Generator Agent)
```python
# LangGraph Node
역할: 최종 분석 결과를 사용자 친화적인 리포트로 변환
입력: 최종 가치 평가 결과
출력: 구조화된 분석 리포트 (텍스트 + 차트 데이터)
도구:
  - report_formatter: 리포트 포맷팅 (Claude 활용)
  - chart_data_generator: 차트 데이터 생성
```

---

## 4. LangGraph 상태 설계

### 4.1 Global State
```python
from typing import TypedDict, Annotated
from langgraph.graph import StateGraph

class AuctionAnalysisState(TypedDict):
    """경매 분석 전체 상태"""
    # 입력
    uploaded_files: list[str]           # 업로드된 파일 경로
    case_number: str | None             # 사건번호

    # 문서 파싱 결과
    parsed_documents: dict | None       # 파싱된 문서 데이터
    parsing_status: str                 # "pending" | "running" | "done" | "error"

    # 권리분석 결과
    rights_analysis: dict | None
    rights_status: str

    # 시장 데이터 결과
    market_data: dict | None
    market_status: str

    # 뉴스 분석 결과
    news_analysis: dict | None
    news_status: str

    # 가치 평가 결과
    valuation: dict | None
    valuation_status: str

    # 최종 리포트
    report: dict | None
    report_status: str

    # 에러 정보
    errors: list[str]
```

### 4.2 체크포인트 전략
- 각 에이전트 노드 완료 시점에 체크포인트 저장
- 에러 발생 시 마지막 체크포인트에서 재시작 가능
- SQLite 기반 체크포인트 저장소 사용

---

## 5. 기능 요구사항

### 5.1 워크플로우 관리
- **FR-06-001**: LangGraph를 사용하여 에이전트 워크플로우를 정의해야 한다
- **FR-06-002**: 독립적인 에이전트 노드들은 병렬로 실행할 수 있어야 한다
- **FR-06-003**: 각 에이전트의 실행 상태(대기/실행중/완료/에러)를 추적해야 한다
- **FR-06-004**: 워크플로우 전체 진행률을 실시간으로 제공해야 한다

### 5.2 에러 처리
- **FR-06-005**: 개별 에이전트 실패 시 전체 워크플로우를 중단하지 않아야 한다
- **FR-06-006**: 실패한 에이전트는 최대 3회까지 재시도해야 한다
- **FR-06-007**: 부분 실패 시 성공한 결과만으로 최종 평가를 수행해야 한다 (graceful degradation)
- **FR-06-008**: 모든 에러와 경고를 로깅해야 한다

### 5.3 DeepAgent 통합
- **FR-06-009**: 권리분석과 가치평가 에이전트에 DeepAgent를 적용해야 한다
- **FR-06-010**: DeepAgent가 사용하는 도구(tools)를 명확히 정의해야 한다
- **FR-06-011**: DeepAgent의 추론 과정(chain of thought)을 로깅해야 한다
- **FR-06-012**: DeepAgent의 토큰 사용량을 모니터링해야 한다

### 5.4 LLM 관리
- **FR-06-013**: Anthropic Claude API를 주 LLM으로 사용해야 한다
- **FR-06-014**: API 호출 비용을 추적하고 제한할 수 있어야 한다
- **FR-06-015**: LLM 응답 시간 타임아웃을 설정할 수 있어야 한다
- **FR-06-016**: 프롬프트 버전 관리가 가능해야 한다

---

## 6. DeepAgent 활용 전략

### 6.1 DeepAgent을 사용하는 이유
| 일반 LangGraph Node | DeepAgent 적용 |
|---------------------|---------------|
| 정해진 도구를 순서대로 호출 | 상황에 따라 도구를 자율적으로 선택/호출 |
| 단순 데이터 변환 | 복잡한 추론이 필요한 분석 |
| 예측 가능한 워크플로우 | 입력에 따라 분석 깊이/방향이 달라짐 |

### 6.2 DeepAgent 적용 에이전트
1. **권리분석 에이전트**: 등기부등본의 복잡한 권리관계를 해석할 때 다양한 법률적 판단이 필요. 상황에 따라 추가 분석이 필요한 경우 자율적으로 도구를 호출.
2. **가치 평가 에이전트**: 여러 분석 결과를 종합할 때 상호 모순되는 데이터가 있을 수 있으며, 이를 자율적으로 판단하여 최종 결론 도출.

### 6.3 DeepAgent 도구 정의
```python
# 권리분석 DeepAgent 도구
rights_tools = [
    {
        "name": "analyze_right_entry",
        "description": "개별 권리 항목의 인수/소멸 여부를 분석",
        "parameters": { "right_entry": "RightEntry 객체" }
    },
    {
        "name": "check_opposition_right",
        "description": "임차인의 대항력 유무를 판단",
        "parameters": { "tenant": "TenantInfo 객체", "basis_date": "말소기준일" }
    },
    {
        "name": "calculate_dividend",
        "description": "배당 순서와 예상 배당액을 계산",
        "parameters": { "creditors": "채권자 목록", "sale_price": "예상 매각가" }
    }
]

# 가치평가 DeepAgent 도구
valuation_tools = [
    {
        "name": "calculate_acquisition_tax",
        "description": "취득세를 계산",
        "parameters": { "price": "낙찰가", "property_type": "부동산유형" }
    },
    {
        "name": "estimate_repair_cost",
        "description": "수리/리모델링 비용을 추정",
        "parameters": { "condition_report": "현황조사 결과" }
    },
    {
        "name": "calculate_roi",
        "description": "투자 수익률을 계산",
        "parameters": { "investment": "총투자비용", "expected_return": "예상수익" }
    }
]
```

---

## 7. 비기능 요구사항

- **전체 분석 시간**: 5분 이내 완료 (PDF 업로드부터 리포트 생성까지)
- **병렬 처리**: 최소 3개 에이전트 동시 실행 가능
- **안정성**: 개별 에이전트 실패 시 전체 시스템 복구 가능
- **비용 관리**: 분석 건당 LLM API 비용 추적
- **로깅**: 모든 에이전트의 입출력 및 실행 이력 로깅

---

## 8. 추후 상세화 필요 사항
- [ ] LangGraph 그래프 구조 상세 코드 설계
- [ ] DeepAgent 초기화 및 도구 바인딩 상세 구현
- [ ] 상태 관리 및 체크포인트 전략 상세화
- [ ] 에러 처리 및 재시도 전략 상세화
- [ ] 프롬프트 엔지니어링 (에이전트별 시스템 프롬프트)
- [ ] LLM 비용 최적화 전략 (모델 선택, 토큰 관리)
- [ ] 모니터링 및 관측성 (LangSmith 연동 등)
- [ ] DeepAgent 최신 API 조사 및 통합 방법 확정
