"""Analysis CRUD and workflow trigger endpoints."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, Query, UploadFile
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.agents.graph import run_analysis_workflow
from app.api.deps import get_db
from app.config import settings
from app.database import async_session
from app.models.analysis import Analysis, AnalysisStatus
from app.models.file import UploadedFile

logger = logging.getLogger("app.analyses")

router = APIRouter()


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
    files: list[UploadFile] = [],
    description: str | None = Form(None),
    case_number: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """새 분석 작업을 생성하고 백그라운드 워크플로우를 시작합니다.

    파일과 메타데이터를 multipart/form-data로 함께 받습니다.
    파일이 없으면 분석을 생성만 하고 워크플로우는 시작하지 않습니다.
    """
    analysis = Analysis()
    analysis.description = description
    analysis.case_number = case_number
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)

    # 파일 저장
    file_paths: list[str] = []
    upload_dir = Path(settings.upload_dir) / analysis.id
    upload_dir.mkdir(parents=True, exist_ok=True)

    for f in files:
        if not f.filename or not f.filename.lower().endswith(".pdf"):
            continue
        file_id = str(uuid4())
        suffix = Path(f.filename).suffix
        stored_path = upload_dir / f"{file_id}{suffix}"
        with open(stored_path, "wb") as buf:
            shutil.copyfileobj(f.file, buf)

        uploaded = UploadedFile(
            id=file_id,
            analysis_id=analysis.id,
            filename=f.filename,
            stored_path=str(stored_path),
            file_size=stored_path.stat().st_size,
        )
        db.add(uploaded)
        file_paths.append(str(stored_path))

    await db.commit()

    # 파일이 있을 때만 워크플로우 시작
    if file_paths:
        background_tasks.add_task(run_analysis_workflow, analysis.id, file_paths)

    logger.debug("created analysis: %s with %d files", analysis.id, len(file_paths))
    return {"id": analysis.id, "status": analysis.status.value}


@router.get("")
async def list_analyses(
    db: AsyncSession = Depends(get_db),
    search: str | None = Query(None, description="검색어 (사건번호, 물건명, 주소, 설명)"),
    sort_by: str = Query("created_at", description="정렬 기준"),
    sort_order: str = Query("desc", description="정렬 방향 (asc/desc)"),
    favorites_only: bool = Query(False, description="즐겨찾기만 표시"),
    status: str | None = Query(None, description="상태 필터"),
) -> list[dict]:
    """분석 작업 목록을 조회합니다."""
    query = select(Analysis)

    # Search filter
    if search:
        pattern = f"%{search}%"
        query = query.where(
            or_(
                Analysis.case_number.ilike(pattern),
                Analysis.property_name.ilike(pattern),
                Analysis.property_address.ilike(pattern),
                Analysis.description.ilike(pattern),
            )
        )

    # Favorites filter
    if favorites_only:
        query = query.where(Analysis.is_favorite == True)  # noqa: E712

    # Status filter
    if status:
        query = query.where(Analysis.status == status)

    # Sort
    _SORT_COLUMNS = {
        "created_at": Analysis.created_at,
        "recommendation": Analysis.recommendation,
        "expected_roi": Analysis.expected_roi,
        "appraised_value": Analysis.appraised_value,
    }
    sort_col = _SORT_COLUMNS.get(sort_by, Analysis.created_at)
    if sort_order == "asc":
        query = query.order_by(sort_col.asc().nullslast())
    else:
        query = query.order_by(sort_col.desc().nullslast())

    result = await db.execute(query)
    analyses = result.scalars().all()
    return [
        {
            "id": a.id,
            "status": a.status.value,
            "description": a.description,
            "case_number": a.case_number,
            "created_at": a.created_at.isoformat(),
            "is_favorite": a.is_favorite or False,
            "property_address": a.property_address,
            "property_name": a.property_name,
            "property_type": a.property_type,
            "area": a.area,
            "appraised_value": a.appraised_value,
            "recommendation": a.recommendation,
            "expected_roi": a.expected_roi,
            "confidence_score": a.confidence_score,
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
        "parsed_documents": analysis.parsed_documents,
        "report": analysis.report,
        "rights_analysis": analysis.rights_analysis,
        "market_data": analysis.market_data,
        "news_analysis": analysis.news_analysis,
        "valuation": analysis.valuation,
        "is_favorite": analysis.is_favorite or False,
        "property_address": analysis.property_address,
        "property_name": analysis.property_name,
        "property_type": analysis.property_type,
        "area": analysis.area,
        "appraised_value": analysis.appraised_value,
        "recommendation": analysis.recommendation,
        "expected_roi": analysis.expected_roi,
        "confidence_score": analysis.confidence_score,
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


@router.patch("/{analysis_id}/favorite")
async def toggle_favorite(analysis_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    """분석 작업의 즐겨찾기 상태를 토글합니다."""
    analysis = await db.get(Analysis, analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="분석 작업을 찾을 수 없습니다.")
    analysis.is_favorite = not (analysis.is_favorite or False)
    await db.commit()
    return {"id": analysis.id, "is_favorite": analysis.is_favorite}


@router.delete("/{analysis_id}")
async def delete_analysis(analysis_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    """분석 작업을 삭제합니다."""
    analysis = await db.get(Analysis, analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="분석 작업을 찾을 수 없습니다.")
    await db.delete(analysis)
    await db.commit()
    return {"detail": "삭제되었습니다."}
