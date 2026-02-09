from __future__ import annotations

from typing import Annotated, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


class AgentState(TypedDict):
    """LangGraph 에이전트 전체 상태"""

    messages: Annotated[list[BaseMessage], add_messages]
    auction_case: dict | None      # AuctionCaseInput.model_dump()
    market_data: dict | None       # MarketDataResponse.model_dump()
    analysis_result: dict | None   # FullAnalysisResult.model_dump()
    route: str                     # "all" | "need_more_info"
    current_step: str
    error: str | None
