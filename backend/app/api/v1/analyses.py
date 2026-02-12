"""Analysis CRUD and workflow trigger endpoints."""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.graph import run_analysis_workflow
from app.api.deps import get_db
from app.database import async_session
from app.models.analysis import Analysis, AnalysisStatus

logger = logging.getLogger("app.analyses")

router = APIRouter()


class CreateAnalysisRequest(BaseModel):
    description: str | None = None
    case_number: str | None = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_STAGE_FIELDS = (
    "parsed_documents",
    "rights_analysis",
    "market_data",
    "news_analysis",
    "valuation",
    "report",
)


def _build_progress(analysis: Analysis) -> dict[str, Any]:
    """Build a progress dict from the analysis JSON fields."""
    stages: dict[str, dict[str, Any]] = {}
    done_count = 0
    for field in _STAGE_FIELDS:
        value = getattr(analysis, field, None)
        if value is not None:
            stages[field] = {"status": "done", "progress": 100}
            done_count += 1
        else:
            match analysis.status:
                case AnalysisStatus.RUNNING:
                    stages[field] = {"status": "pending", "progress": 0}
                case AnalysisStatus.ERROR:
                    stages[field] = {"status": "error", "progress": 0}
                case _:
                    stages[field] = {"status": "pending", "progress": 0}

    total = len(_STAGE_FIELDS)
    overall = int(done_count / total * 100) if total else 0
    return {"overall": overall, "stages": stages}


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("", status_code=201)
async def create_analysis(
    background_tasks: BackgroundTasks,
    body: CreateAnalysisRequest | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """새 분석 작업을 생성하고 백그라운드 워크플로우를 시작합니다."""
    analysis = Analysis()
    if body:
        analysis.description = body.description
        analysis.case_number = body.case_number
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)

    background_tasks.add_task(run_analysis_workflow, analysis.id)

    logger.debug("created analysis: %s", analysis.id)
    return {"id": analysis.id, "status": analysis.status.value}


@router.get("")
async def list_analyses(db: AsyncSession = Depends(get_db)) -> list[dict]:
    """분석 작업 목록을 조회합니다."""
    result = await db.execute(select(Analysis).order_by(Analysis.created_at.desc()))
    analyses = result.scalars().all()
    return [
        {
            "id": a.id,
            "status": a.status.value,
            "description": a.description,
            "case_number": a.case_number,
            "created_at": a.created_at.isoformat(),
        }
        for a in analyses
    ]


@router.get("/{analysis_id}")
async def get_analysis(analysis_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    """분석 작업 상세를 조회합니다."""
    analysis = await db.get(Analysis, analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="분석 작업을 찾을 수 없습니다.")
    return {
        "id": analysis.id,
        "status": analysis.status.value,
        "description": analysis.description,
        "case_number": analysis.case_number,
        "created_at": analysis.created_at.isoformat(),
        "started_at": analysis.started_at.isoformat() if analysis.started_at else None,
        "completed_at": analysis.completed_at.isoformat() if analysis.completed_at else None,
        "report": analysis.report,
        "rights_analysis": analysis.rights_analysis,
        "market_data": analysis.market_data,
        "news_analysis": analysis.news_analysis,
        "valuation": analysis.valuation,
    }


@router.get("/{analysis_id}/status")
async def get_analysis_status(
    analysis_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """분석 진행 상태를 조회합니다."""
    analysis = await db.get(Analysis, analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="분석 작업을 찾을 수 없습니다.")

    return {
        "id": analysis.id,
        "status": analysis.status.value,
        "progress": _build_progress(analysis),
        "started_at": analysis.started_at.isoformat() if analysis.started_at else None,
    }


@router.get("/{analysis_id}/report")
async def get_analysis_report(
    analysis_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """분석 리포트를 조회합니다. 분석이 완료되어야 조회 가능합니다."""
    analysis = await db.get(Analysis, analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="분석 작업을 찾을 수 없습니다.")
    if analysis.status != AnalysisStatus.DONE:
        raise HTTPException(status_code=400, detail="분석이 아직 완료되지 않았습니다.")
    return analysis.report or {}


@router.delete("/{analysis_id}")
async def delete_analysis(analysis_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    """분석 작업을 삭제합니다."""
    analysis = await db.get(Analysis, analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="분석 작업을 찾을 수 없습니다.")
    await db.delete(analysis)
    await db.commit()
    return {"detail": "삭제되었습니다."}
