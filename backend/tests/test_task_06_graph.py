"""Task-06: AI 에이전트 시스템 단위 테스트

LangGraph 워크플로우 구성, 노드 실행 순서, 에러 처리를 검증한다.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.agents.graph import (
    NODE_REGISTRY,
    PARALLEL_NODES,
    WORKFLOW_NODES,
    _run_node_with_retry,
)
from app.agents.nodes.report_generator import _safe_dict, report_generator_node
from app.agents.state import AgentState
from app.schemas.valuation import ValuationResult


# ---------------------------------------------------------------------------
# T-1: 워크플로우 노드 등록 검증
# ---------------------------------------------------------------------------


def test_all_nodes_registered():
    """모든 워크플로우 노드가 NODE_REGISTRY에 등록되어 있다."""
    for name in WORKFLOW_NODES:
        assert name in NODE_REGISTRY, f"{name}이 NODE_REGISTRY에 없습니다"
        assert callable(NODE_REGISTRY[name])


# ---------------------------------------------------------------------------
# T-2: 노드 실행 순서 검증
# ---------------------------------------------------------------------------


def test_node_order():
    """document_parser → 병렬(rights, market, news) → valuation → report 순서."""
    assert WORKFLOW_NODES[0] == "document_parser"

    # 병렬 노드들이 document_parser 뒤에 위치
    for parallel_name in PARALLEL_NODES:
        idx = WORKFLOW_NODES.index(parallel_name)
        assert idx > 0, f"{parallel_name}은 document_parser 뒤에 와야 합니다"
        assert idx < WORKFLOW_NODES.index("valuation"), f"{parallel_name}은 valuation 앞에 와야 합니다"

    # valuation → report_generator 순서
    assert WORKFLOW_NODES.index("valuation") < WORKFLOW_NODES.index("report_generator")


# ---------------------------------------------------------------------------
# T-3: 재시도 동작 검증
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_retry_on_failure():
    """노드 실패 시 3회 재시도 후 에러를 기록한다."""
    call_count = 0

    async def failing_node(state: AgentState) -> AgentState:
        nonlocal call_count
        call_count += 1
        raise ValueError("테스트 에러")

    state = AgentState(analysis_id="test-retry")

    # asyncio.sleep을 mock하여 대기 시간 제거
    with patch("app.agents.graph.asyncio.sleep", new_callable=AsyncMock):
        result = await _run_node_with_retry("test_node", failing_node, state, max_retries=3)

    assert call_count == 3
    assert len(result.errors) == 1
    assert "test_node 실패" in result.errors[0]


# ---------------------------------------------------------------------------
# T-4: Graceful degradation (부분 실패)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_graceful_degradation():
    """일부 분석 노드가 실패해도 나머지 결과로 평가를 진행할 수 있다."""
    from app.agents.nodes.valuation import valuation_node
    from app.schemas.document import AppraisalExtraction

    # rights_analysis=None, market_data=None이지만 감정가로 평가 가능
    state = AgentState(
        analysis_id="test-graceful",
        appraisal=AppraisalExtraction(appraised_value=500_000_000),
    )

    result = await valuation_node(state)

    # 감정가 fallback으로 평가 수행됨
    assert result.valuation is not None
    assert result.valuation.bid_price.moderate > 0


# ---------------------------------------------------------------------------
# T-5: report_generator_node 테스트
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_report_generator_node():
    """report_generator_node가 Claude 응답을 파싱하여 report를 생성한다."""
    mock_response = '{"property_overview": "테스트 물건", "rights_summary": "권리 요약", "market_summary": "시세 요약", "news_summary": "뉴스 요약", "overall_opinion": "종합 의견"}'

    state = AgentState(
        analysis_id="test-report",
        valuation=ValuationResult(),
    )

    with patch(
        "app.agents.nodes.report_generator._call_llm",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        result = await report_generator_node(state)

    assert result.report is not None
    assert "analysis_summary" in result.report
    assert result.report["analysis_summary"]["property_overview"] == "테스트 물건"
    assert len(result.errors) == 0


# ---------------------------------------------------------------------------
# T-6: _safe_dict 유틸리티
# ---------------------------------------------------------------------------


def test_safe_dict_none():
    """None 입력 시 '없음' 반환."""
    assert _safe_dict(None) == "없음"


def test_safe_dict_dataclass():
    """dataclass를 JSON 문자열로 변환."""
    result = _safe_dict(ValuationResult())
    assert "recommendation" in result
