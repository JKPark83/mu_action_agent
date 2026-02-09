"""LangGraph 워크플로우 정의"""
from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from src.agent.nodes import (
    analyze_bid_price,
    analyze_rights,
    estimate_sale_price,
    fetch_market_data,
    parse_input,
    respond,
    route_decision,
    router,
    synthesize,
)
from src.agent.state import AgentState


def build_graph() -> StateGraph:
    """경매 분석 LangGraph 워크플로우를 빌드하고 컴파일한다."""

    workflow = StateGraph(AgentState)

    # 노드 등록
    workflow.add_node("parse_input", parse_input)
    workflow.add_node("router", router)
    workflow.add_node("fetch_market_data", fetch_market_data)
    workflow.add_node("analyze_bid_price", analyze_bid_price)
    workflow.add_node("analyze_rights", analyze_rights)
    workflow.add_node("estimate_sale_price", estimate_sale_price)
    workflow.add_node("synthesize", synthesize)
    workflow.add_node("respond", respond)

    # 엣지 정의
    workflow.add_edge(START, "parse_input")
    workflow.add_edge("parse_input", "router")

    # 조건부 라우팅: all → 전체 분석, need_more_info → 응답(추가입력 요청)
    workflow.add_conditional_edges(
        "router",
        route_decision,
        {
            "all": "fetch_market_data",
            "need_more_info": "respond",
        },
    )

    # 시세 조회 → 입찰가 분석
    workflow.add_edge("fetch_market_data", "analyze_bid_price")

    # 입찰가 분석 → 권리분석
    workflow.add_edge("analyze_bid_price", "analyze_rights")

    # 권리분석 → 매도가 추정
    workflow.add_edge("analyze_rights", "estimate_sale_price")

    # 매도가 추정 → 종합
    workflow.add_edge("estimate_sale_price", "synthesize")

    # 종합 → 응답
    workflow.add_edge("synthesize", "respond")

    # 응답 → 종료
    workflow.add_edge("respond", END)

    return workflow.compile()
