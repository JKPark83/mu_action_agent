import logging
import sys
from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import api_router
from app.config import settings
from app.database import engine, Base


def _setup_logging() -> None:
    """애플리케이션 로깅을 설정한다."""
    log_format = "%(asctime)s [%(levelname)-7s] %(name)s: %(message)s"
    date_format = "%H:%M:%S"
    level = logging.DEBUG if settings.debug else logging.INFO

    logging.basicConfig(
        level=level,
        format=log_format,
        datefmt=date_format,
        stream=sys.stderr,
        force=True,
    )

    # 외부 라이브러리 로그는 WARNING 이상만, 앱 로그만 상세 출력
    logging.getLogger().setLevel(logging.WARNING)
    logging.getLogger("app").setLevel(level)

    # pdfminer: 폰트 메타데이터 누락 경고가 반복되므로 ERROR 이상만 출력
    logging.getLogger("pdfminer").setLevel(logging.ERROR)

    # 분석 파이프라인 로그: debug 모드일 때만 상세 출력
    if settings.debug:
        logging.getLogger("app.agents").setLevel(logging.DEBUG)


_setup_logging()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    # Startup: create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    # Shutdown
    await engine.dispose()


app = FastAPI(
    title="부동산 경매 분석 AI",
    description="부동산 경매 물건을 AI로 분석하여 입찰 추천, 적정 입찰가, 예상 매도가, 투자 수익률을 제공합니다.",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")
