from __future__ import annotations

import os

from dotenv import load_dotenv
from langchain_core.language_models import BaseChatModel

load_dotenv()


def create_llm(
    provider: str | None = None,
    model: str | None = None,
) -> BaseChatModel:
    """LLM 팩토리 함수. provider/model 미지정 시 환경변수에서 로드한다."""
    provider = provider or os.getenv("LLM_PROVIDER", "openai")
    model = model or os.getenv("LLM_MODEL", "") or None

    if provider == "openai":
        api_key = os.getenv("OPENAI_API_KEY", "")
        if not api_key or api_key.startswith("sk-..."):
            raise ValueError(
                "OPENAI_API_KEY가 설정되지 않았습니다. "
                ".env 파일에 유효한 OpenAI API 키를 입력하세요."
            )
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(
            api_key=api_key,
            model=model or "gpt-4o",
            temperature=0.1,
        )

    if provider == "anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not api_key or api_key.startswith("sk-ant-..."):
            raise ValueError(
                "ANTHROPIC_API_KEY가 설정되지 않았습니다. "
                ".env 파일에 유효한 Anthropic API 키를 입력하세요."
            )
        from langchain_anthropic import ChatAnthropic

        return ChatAnthropic(
            api_key=api_key,
            model=model or "claude-sonnet-4-20250514",
            temperature=0.1,
        )

    raise ValueError(f"지원하지 않는 LLM 프로바이더: {provider}")
