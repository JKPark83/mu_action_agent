"""Streamlit UI 컴포넌트"""
from __future__ import annotations

import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage

from src.agent.graph import build_graph
from src.models.schemas import PropertyType, RightType


# ---------------------------------------------------------------------------
# 그래프 캐시
# ---------------------------------------------------------------------------

@st.cache_resource
def get_graph():
    return build_graph()


# ---------------------------------------------------------------------------
# 세션 상태 초기화
# ---------------------------------------------------------------------------

def init_session():
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "rights_count" not in st.session_state:
        st.session_state.rights_count = 0


# ---------------------------------------------------------------------------
# 사이드바: 경매사건 정보 + 권리관계 입력
# ---------------------------------------------------------------------------

def render_sidebar() -> dict | None:
    """사이드바 폼을 렌더링하고, 분석 시작 시 입력 데이터 dict를 반환한다."""
    with st.sidebar:
        st.header("경매사건 정보 입력")

        address = st.text_input("소재지 주소 *", placeholder="예: 서울특별시 강남구 대치동 XX아파트")
        property_type = st.selectbox(
            "물건종류 *",
            [pt.value for pt in PropertyType],
            index=0,
        )
        appraisal = st.number_input("감정가 (원) *", min_value=0, step=10_000_000, format="%d")
        minimum_bid = st.number_input("최저매각가격 (원) *", min_value=0, step=10_000_000, format="%d")
        area = st.number_input("전용면적 (m2)", min_value=0.0, step=1.0, format="%.2f")
        case_number = st.text_input("사건번호", placeholder="예: 2024타경12345")
        court = st.text_input("관할법원", placeholder="예: 서울중앙지방법원")
        bid_count = st.number_input("유찰횟수", min_value=0, step=1, value=0)

        # ── 권리관계 동적 입력 ──
        st.subheader("권리관계")
        col_add, col_remove = st.columns(2)
        with col_add:
            if st.button("+ 권리 추가"):
                st.session_state.rights_count += 1
        with col_remove:
            if st.button("- 권리 삭제") and st.session_state.rights_count > 0:
                st.session_state.rights_count -= 1

        rights = []
        for i in range(st.session_state.rights_count):
            with st.expander(f"권리 {i + 1}", expanded=True):
                rt = st.selectbox(f"유형##{i}", [r.value for r in RightType], key=f"rt_{i}")
                creditor = st.text_input(f"권리자##{i}", key=f"cred_{i}")
                amount = st.number_input(f"금액 (원)##{i}", min_value=0, step=1_000_000, key=f"amt_{i}", format="%d")
                date = st.text_input(f"설정일 (YYYY-MM-DD)##{i}", key=f"date_{i}")
                is_senior = st.checkbox(f"선순위 여부##{i}", key=f"senior_{i}")
                rights.append({
                    "type": rt,
                    "creditor": creditor,
                    "amount": amount,
                    "date": date,
                    "is_senior": is_senior,
                    "note": "",
                })

        # ── LLM 설정 ──
        st.divider()
        st.subheader("LLM 설정")
        llm_provider = st.radio("프로바이더", ["openai", "anthropic"], index=0)
        st.session_state["llm_provider"] = llm_provider

        # ── 분석 시작 버튼 ──
        st.divider()
        if st.button("분석 시작", type="primary", use_container_width=True):
            if not address or appraisal <= 0 or minimum_bid <= 0:
                st.error("소재지 주소, 감정가, 최저매각가격은 필수입니다.")
                return None
            return {
                "address": address,
                "property_type": property_type,
                "appraisal_value": int(appraisal),
                "minimum_bid": int(minimum_bid),
                "area_m2": area if area > 0 else None,
                "case_number": case_number or None,
                "court": court or None,
                "bid_count": bid_count,
                "rights": rights,
            }

    return None


# ---------------------------------------------------------------------------
# 메인 영역: 채팅 UI
# ---------------------------------------------------------------------------

def render_chat():
    """채팅 메시지 히스토리를 표시한다."""
    for msg in st.session_state.messages:
        role = "user" if isinstance(msg, HumanMessage) else "assistant"
        with st.chat_message(role):
            st.markdown(msg.content)


# ---------------------------------------------------------------------------
# 분석 실행
# ---------------------------------------------------------------------------

def run_analysis(form_data: dict):
    """폼 데이터로 LangGraph 에이전트를 실행한다."""
    import json

    # 사용자 메시지 구성
    user_text = (
        f"다음 경매 물건을 분석해주세요:\n"
        f"주소: {form_data['address']}\n"
        f"물건종류: {form_data['property_type']}\n"
        f"감정가: {form_data['appraisal_value']:,}원\n"
        f"최저매각가격: {form_data['minimum_bid']:,}원\n"
    )
    if form_data.get("area_m2"):
        user_text += f"전용면적: {form_data['area_m2']}m2\n"
    if form_data.get("bid_count"):
        user_text += f"유찰횟수: {form_data['bid_count']}회\n"
    if form_data.get("rights"):
        user_text += f"권리관계: {json.dumps(form_data['rights'], ensure_ascii=False)}\n"

    user_msg = HumanMessage(content=user_text)
    st.session_state.messages.append(user_msg)

    with st.chat_message("user"):
        st.markdown(user_text)

    # 에이전트 실행
    graph = get_graph()
    initial_state = {
        "messages": [user_msg],
        "auction_case": None,
        "market_data": None,
        "analysis_result": None,
        "route": "",
        "current_step": "start",
        "error": None,
    }

    with st.chat_message("assistant"):
        with st.spinner("분석 중입니다..."):
            try:
                result = graph.invoke(initial_state)
            except Exception as e:
                st.error(f"분석 실행 중 오류: {e}")
                return

        # 결과 메시지 표시
        msgs = result.get("messages", [])
        if msgs:
            last = msgs[-1]
            content = last.content if hasattr(last, "content") else str(last)
            st.markdown(content)
            st.session_state.messages.append(AIMessage(content=content))

        # 구조화된 결과 표시
        analysis = result.get("analysis_result")
        if analysis:
            _render_analysis_metrics(analysis)


def _render_analysis_metrics(analysis: dict):
    """분석 결과를 st.metric / st.dataframe 으로 구조화 표시"""
    bid = analysis.get("bid_recommendation")
    if bid:
        st.subheader("추천 입찰가")
        c1, c2, c3 = st.columns(3)
        c1.metric("최저 입찰가", f"{bid['min_bid']:,}원")
        c2.metric("최적 입찰가", f"{bid['optimal_bid']:,}원")
        c3.metric("최고 입찰가", f"{bid['max_bid']:,}원")

    rights = analysis.get("rights_assessment")
    if rights:
        grade = rights["risk_grade"]
        label = rights["risk_grade_label"]
        color_map = {"A": "green", "B": "orange", "C": "red", "D": "red"}
        color = color_map.get(grade, "gray")
        st.subheader("권리분석")
        st.markdown(
            f"리스크 등급: :{color}[**{grade} ({label})**]"
        )
        st.write(rights["summary"])

    market = analysis.get("market_data")
    if market and market.get("recent_transactions"):
        st.subheader("최근 거래 내역")
        import pandas as pd

        df = pd.DataFrame(market["recent_transactions"])
        if not df.empty:
            df = df.rename(columns={
                "deal_date": "거래월",
                "deal_amount": "거래금액(원)",
                "area_m2": "면적(m2)",
                "floor": "층",
                "building_name": "건물명",
            })
            st.dataframe(df, use_container_width=True)

    sale = analysis.get("sale_estimate")
    if sale:
        st.subheader("수익성 분석")
        c1, c2, c3 = st.columns(3)
        c1.metric("현실적 매도가", f"{sale['realistic']:,}원")
        c2.metric("순수익 추정", f"{sale['net_profit_estimate']:,}원")
        c3.metric("수익률", f"{sale['roi_percent']}%")


# ---------------------------------------------------------------------------
# 면책 고지
# ---------------------------------------------------------------------------

def render_disclaimer():
    st.divider()
    st.caption(
        "**[면책 고지]** "
        "본 서비스는 AI 기반의 참고용 분석 도구입니다. "
        "제공되는 모든 분석 결과는 투자 권유가 아니며, 투자 판단의 책임은 사용자에게 있습니다. "
        "권리분석은 법률 전문가의 검토를 대체할 수 없습니다. "
        "시세 및 수익률 추정은 실제와 다를 수 있습니다. "
        "세금 관련 사항은 세무 전문가와 상담하시기 바랍니다."
    )
