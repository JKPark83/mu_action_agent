"""부동산 경매 분석 AI 에이전트 – Streamlit 엔트리포인트"""

from dotenv import load_dotenv

load_dotenv()

import streamlit as st

from ui.app import (
    init_session,
    render_chat,
    render_disclaimer,
    render_sidebar,
    run_analysis,
)

st.set_page_config(
    page_title="부동산 경매 분석 AI",
    page_icon="🏠",
    layout="wide",
)

st.title("부동산 경매 분석 AI 에이전트")

init_session()

# 사이드바 입력
form_data = render_sidebar()

# 채팅 히스토리
render_chat()

# 자유 채팅 입력
user_input = st.chat_input("질문을 입력하세요 (예: 이 물건의 시세를 알려줘)")
if user_input:
    from langchain_core.messages import AIMessage, HumanMessage

    user_msg = HumanMessage(content=user_input)
    st.session_state.messages.append(user_msg)
    with st.chat_message("user"):
        st.markdown(user_input)

    # 자유 채팅도 그래프로 실행
    from ui.app import get_graph

    graph = get_graph()
    with st.chat_message("assistant"):
        with st.spinner("처리 중..."):
            try:
                result = graph.invoke({
                    "messages": st.session_state.messages,
                    "auction_case": None,
                    "market_data": None,
                    "analysis_result": None,
                    "route": "",
                    "current_step": "start",
                    "error": None,
                })
                msgs = result.get("messages", [])
                if msgs:
                    last = msgs[-1]
                    content = last.content if hasattr(last, "content") else str(last)
                    st.markdown(content)
                    st.session_state.messages.append(AIMessage(content=content))
            except Exception as e:
                st.error(f"오류 발생: {e}")

# 폼 분석 시작
if form_data:
    run_analysis(form_data)

# 면책 고지
render_disclaimer()
