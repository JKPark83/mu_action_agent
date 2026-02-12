# Task-06: AI 에이전트 시스템 (LangGraph 워크플로우)

> **참조 스펙**: PRD-06 전체
> **예상 작업 시간**: 5~7시간
> **선행 작업**: Task-01~05 (모든 에이전트 노드 구현 완료)
> **변경 파일 수**: 3~5개

---

## 목차

1. [LangGraph StateGraph 구성](#1-langgraph-stategraph-구성)
2. [병렬 실행 설정](#2-병렬-실행-설정)
3. [리포트 생성 노드](#3-리포트-생성-노드)
4. [에러 처리 및 재시도](#4-에러-처리-및-재시도)
5. [워크플로우 실행 함수](#5-워크플로우-실행-함수)
6. [테스트 가이드](#6-테스트-가이드)

---

## 1. LangGraph StateGraph 구성

### 1.1 그래프 정의

> 파일: `backend/app/agents/graph.py`
> 참조 상태: `backend/app/agents/state.py`

```python
from langgraph.graph import StateGraph, END

from app.agents.state import AgentState
from app.agents.nodes.document_parser import document_parser_node
from app.agents.nodes.rights_analysis import rights_analysis_node
from app.agents.nodes.market_data import market_data_node
from app.agents.nodes.news_analysis import news_analysis_node
from app.agents.nodes.valuation import valuation_node
from app.agents.nodes.report_generator import report_generator_node


def build_analysis_graph() -> StateGraph:
    """경매 분석 LangGraph 워크플로우 구성"""

    graph = StateGraph(AgentState)

    # 노드 등록
    graph.add_node("document_parser", document_parser_node)
    graph.add_node("rights_analysis", rights_analysis_node)
    graph.add_node("market_data", market_data_node)
    graph.add_node("news_analysis", news_analysis_node)
    graph.add_node("valuation", valuation_node)
    graph.add_node("report_generator", report_generator_node)

    # 엣지 정의: 실행 순서
    graph.set_entry_point("document_parser")

    # 문서 파싱 → 3개 병렬 분석
    graph.add_edge("document_parser", "rights_analysis")
    graph.add_edge("document_parser", "market_data")
    graph.add_edge("document_parser", "news_analysis")

    # 병렬 분석 → 가치 평가
    graph.add_edge("rights_analysis", "valuation")
    graph.add_edge("market_data", "valuation")
    graph.add_edge("news_analysis", "valuation")

    # 가치 평가 → 리포트 생성
    graph.add_edge("valuation", "report_generator")

    # 리포트 생성 → 종료
    graph.add_edge("report_generator", END)

    return graph.compile()
```

### 1.2 AgentState 보완

> 파일: `backend/app/agents/state.py`

기존 상태에 진행률 추적 필드를 추가합니다.

```python
from typing import TypedDict

class AgentState(TypedDict):
    # 입력
    analysis_id: str
    file_paths: list[str]

    # 문서 파싱
    registry: dict | None
    appraisal: dict | None
    sale_item: dict | None

    # 분석 결과
    rights_analysis: dict | None
    market_data: dict | None
    news_analysis: dict | None
    valuation: dict | None
    report: dict | None

    # 에러
    errors: list[str]

    # 진행률 (WebSocket 전송용)
    current_stage: str
    stage_progress: dict[str, int]
```

---

## 2. 병렬 실행 설정

### 2.1 LangGraph 병렬 노드

LangGraph에서 동일 소스 노드에서 여러 목적 노드로 엣지를 추가하면 자동으로 병렬 실행됩니다.

```python
# document_parser → [rights_analysis, market_data, news_analysis] 병렬 실행
graph.add_edge("document_parser", "rights_analysis")
graph.add_edge("document_parser", "market_data")
graph.add_edge("document_parser", "news_analysis")
```

### 2.2 병렬 결과 수집

`valuation` 노드는 3개 병렬 노드 모두 완료될 때까지 대기합니다. LangGraph가 자동으로 처리합니다.

---

## 3. 리포트 생성 노드

### 3.1 report_generator 노드

> 파일: `backend/app/agents/nodes/report_generator.py`

```python
from anthropic import Anthropic

REPORT_PROMPT = """
다음 분석 결과를 기반으로 경매 분석 리포트를 생성해주세요.
비전문가도 쉽게 이해할 수 있는 용어를 사용하세요.

권리분석 결과: {rights}
시장 데이터: {market}
뉴스 분석: {news}
가치 평가: {valuation}

리포트 구조:
1. property_overview: 물건 개요 (2~3문장)
2. rights_summary: 권리분석 핵심 요약 (3~5문장)
3. market_summary: 시세 분석 요약 (3~5문장)
4. news_summary: 뉴스/동향 요약 (3~5문장)
5. overall_opinion: 종합 의견 (5~7문장)

JSON으로 응답해주세요.
"""

async def report_generator_node(state: AgentState) -> AgentState:
    """
    처리 흐름:
    1. 모든 분석 결과 수집
    2. Claude로 사용자 친화적 리포트 텍스트 생성
    3. 차트 데이터 구성 (시세 추이, 비용 분해 등)
    4. 최종 report dict 생성하여 state에 저장
    """
    client = Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=3000,
        messages=[{
            "role": "user",
            "content": REPORT_PROMPT.format(
                rights=state.get("rights_analysis"),
                market=state.get("market_data"),
                news=state.get("news_analysis"),
                valuation=state.get("valuation"),
            ),
        }],
    )

    report_text = parse_json_response(response)

    # 최종 리포트 조합
    report = {
        **state.get("valuation", {}),
        "analysis_summary": report_text,
        "chart_data": build_chart_data(state),
    }

    return {**state, "report": report}


def build_chart_data(state: AgentState) -> dict:
    """프론트엔드 차트용 데이터 구성"""
    market = state.get("market_data")
    costs = state.get("valuation", {}).get("cost_breakdown", {})

    return {
        "price_trend": market.get("price_trend", {}).get("monthly_data", {}) if market else {},
        "cost_breakdown_chart": costs,
    }
```

---

## 4. 에러 처리 및 재시도

### 4.1 노드별 에러 래퍼

```python
import asyncio
from functools import wraps

def with_retry(max_retries: int = 3, stage_name: str = ""):
    """에이전트 노드 재시도 데코레이터"""
    def decorator(func):
        @wraps(func)
        async def wrapper(state: AgentState) -> AgentState:
            for attempt in range(max_retries):
                try:
                    return await func(state)
                except Exception as e:
                    if attempt == max_retries - 1:
                        errors = state.get("errors", [])
                        errors.append(f"{stage_name} 실패: {str(e)}")
                        return {**state, "errors": errors}
                    await asyncio.sleep(2 ** attempt)  # exponential backoff
        return wrapper
    return decorator

# 사용 예
@with_retry(max_retries=3, stage_name="권리분석")
async def rights_analysis_node(state: AgentState) -> AgentState:
    ...
```

### 4.2 Graceful Degradation

```python
async def valuation_node(state: AgentState) -> AgentState:
    """부분 실패 시에도 가능한 범위에서 결과 생성"""
    rights = state.get("rights_analysis")  # None일 수 있음
    market = state.get("market_data")       # None일 수 있음
    news = state.get("news_analysis")       # None일 수 있음

    # 최소 1개 결과가 있으면 가치 평가 시도
    if not any([rights, market, news]):
        return {**state, "valuation": None, "errors": state.get("errors", []) + ["모든 분석 실패"]}

    # 가용한 데이터만으로 평가 수행
    ...
```

---

## 5. 워크플로우 실행 함수

### 5.1 분석 실행 엔트리포인트

> 파일: `backend/app/agents/graph.py`

```python
from app.api.websocket.manager import manager

async def run_analysis_workflow(
    analysis_id: str,
    file_paths: list[str],
    db_session_factory,
) -> dict:
    """
    분석 워크플로우 실행 (BackgroundTask에서 호출)

    1. Analysis 상태를 "running"으로 업데이트
    2. LangGraph 워크플로우 실행
    3. 각 노드 완료 시 WebSocket 진행 상태 전송
    4. 최종 결과를 DB에 저장
    5. Analysis 상태를 "done" 또는 "error"로 업데이트
    """
    graph = build_analysis_graph()

    initial_state: AgentState = {
        "analysis_id": analysis_id,
        "file_paths": file_paths,
        "registry": None,
        "appraisal": None,
        "sale_item": None,
        "rights_analysis": None,
        "market_data": None,
        "news_analysis": None,
        "valuation": None,
        "report": None,
        "errors": [],
        "current_stage": "document_parser",
        "stage_progress": {},
    }

    # DB 상태 업데이트: running
    async with db_session_factory() as session:
        analysis = await session.get(Analysis, analysis_id)
        analysis.status = "running"
        analysis.started_at = datetime.utcnow()
        await session.commit()

    try:
        # 그래프 실행
        result = await graph.ainvoke(initial_state)

        # DB 저장
        async with db_session_factory() as session:
            analysis = await session.get(Analysis, analysis_id)
            analysis.status = "done"
            analysis.report = result.get("report")
            analysis.rights_analysis = result.get("rights_analysis")
            analysis.market_data = result.get("market_data")
            analysis.news_analysis = result.get("news_analysis")
            analysis.valuation = result.get("valuation")
            analysis.completed_at = datetime.utcnow()
            analysis.errors = result.get("errors")
            await session.commit()

        # WebSocket 완료 알림
        await manager.send_progress(analysis_id, {
            "type": "analysis_complete",
            "report_url": f"/api/v1/analyses/{analysis_id}/report",
        })

    except Exception as e:
        async with db_session_factory() as session:
            analysis = await session.get(Analysis, analysis_id)
            analysis.status = "error"
            analysis.errors = [str(e)]
            await session.commit()
```

---

## 6. 테스트 가이드

### 6.1 테스트 케이스

| ID | 테스트명 | 설명 | 기대 결과 |
|:---:|:---|:---|:---|
| T-1 | `test_build_graph` | 그래프 빌드 성공 | 컴파일 에러 없음 |
| T-2 | `test_graph_node_order` | 노드 실행 순서 | parser → 병렬 → valuation → report |
| T-3 | `test_retry_on_failure` | 노드 실패 → 재시도 | 3회 재시도 후 에러 |
| T-4 | `test_graceful_degradation` | 부분 실패 | 가용 데이터로 결과 생성 |
| T-5 | `test_run_workflow_updates_db` | 전체 실행 | DB status=done |
| T-6 | `test_report_generator` | 리포트 생성 | report dict 반환 |

### 6.2 테스트 실행

```bash
cd backend
uv run pytest tests/unit/agents/test_graph.py -v
uv run pytest tests/integration/test_workflow.py -v
```

---

## 파일 변경 요약

### 수정 파일

| 파일 경로 | 변경 내용 |
|:---|:---|
| `backend/app/agents/graph.py` | LangGraph StateGraph 전체 구현 |
| `backend/app/agents/state.py` | 진행률 필드 추가 |
| `backend/app/agents/nodes/report_generator.py` | 리포트 생성 노드 구현 |

### 신규 생성 파일

| 파일 경로 | 설명 |
|:---|:---|
| `backend/app/agents/prompts/report_prompts.py` | 리포트 생성 프롬프트 |
| `backend/tests/unit/agents/test_graph.py` | 그래프 단위 테스트 |
| `backend/tests/integration/test_workflow.py` | 워크플로우 통합 테스트 |
