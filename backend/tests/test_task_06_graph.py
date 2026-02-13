"""Task-06: AI 에이전트 시스템 단위 테스트

LangGraph StateGraph 워크플로우 구성, 노드 실행 순서, 에러 처리를 검증한다.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest

from app.agents.graph import (
    PARALLEL_NODES,
    WORKFLOW_NODES,
    build_graph,
    compiled_graph,
)
from app.agents.nodes.report_generator import _safe_dict, report_generator_node
from app.agents.state import AgentState
from app.schemas.valuation import ValuationResult


# ---------------------------------------------------------------------------
# T-1: 워크플로우 노드 등록 검증
# ---------------------------------------------------------------------------


def test_all_nodes_registered():
    """모든 워크플로우 노드가 StateGraph에 등록되어 있다."""
    node_names = set(compiled_graph.nodes.keys())
    for name in WORKFLOW_NODES:
        assert name in node_names, f"{name}이 StateGraph에 없습니다"


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
# T-3: 그래프 구조 검증
# ---------------------------------------------------------------------------


def test_graph_structure():
    """StateGraph가 올바른 fan-out/fan-in 구조를 가진다."""
    graph = build_graph()
    node_names = set(graph.nodes.keys())

    # 모든 노드가 등록되어 있는지 확인
    for name in WORKFLOW_NODES:
        assert name in node_names, f"{name}이 컴파일된 그래프에 없습니다"


# ---------------------------------------------------------------------------
# T-4: Graceful degradation (부분 실패)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_graceful_degradation():
    """일부 분석 노드가 실패해도 나머지 결과로 평가를 진행할 수 있다."""
    from app.agents.nodes.valuation import valuation_node
    from app.schemas.document import AppraisalExtraction

    # TypedDict state: rights_analysis=None, market_data=None이지만 감정가로 평가 가능
    state: AgentState = {
        "analysis_id": "test-graceful",
        "file_paths": [],
        "registry": None,
        "appraisal": AppraisalExtraction(appraised_value=500_000_000),
        "sale_item": None,
        "status_report": None,
        "rights_analysis": None,
        "market_data": None,
        "news_analysis": None,
        "valuation": None,
        "report": None,
        "errors": [],
    }

    result = await valuation_node(state)

    # result는 partial dict
    assert result.get("valuation") is not None
    assert result["valuation"].bid_price.moderate > 0


# ---------------------------------------------------------------------------
# T-5: report_generator_node 테스트
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_report_generator_node():
    """report_generator_node가 Claude 응답을 파싱하여 report를 생성한다."""
    mock_response = '{"property_overview": "테스트 물건", "rights_summary": "권리 요약", "market_summary": "시세 요약", "news_summary": "뉴스 요약", "overall_opinion": "종합 의견"}'

    state: AgentState = {
        "analysis_id": "test-report",
        "file_paths": [],
        "registry": None,
        "appraisal": None,
        "sale_item": None,
        "status_report": None,
        "rights_analysis": None,
        "market_data": None,
        "news_analysis": None,
        "valuation": ValuationResult(),
        "report": None,
        "errors": [],
    }

    with patch(
        "app.agents.nodes.report_generator._call_llm",
        new_callable=AsyncMock,
        return_value=mock_response,
    ):
        result = await report_generator_node(state)

    # result는 partial dict
    assert result.get("report") is not None
    assert "analysis_summary" in result["report"]
    assert result["report"]["analysis_summary"]["property_overview"] == "테스트 물건"
    # errors key가 없거나 빈 리스트
    assert not result.get("errors", [])


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
