from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.analysis import Analysis

router = APIRouter()


@router.post("")
async def create_analysis(db: AsyncSession = Depends(get_db)) -> dict:
    """새 분석 작업을 생성합니다."""
    analysis = Analysis()
    db.add(analysis)
    await db.commit()
    await db.refresh(analysis)
    return {"id": analysis.id, "status": analysis.status.value}


@router.get("")
async def list_analyses(db: AsyncSession = Depends(get_db)) -> list[dict]:
    """분석 작업 목록을 조회합니다."""
    result = await db.execute(select(Analysis).order_by(Analysis.created_at.desc()))
    analyses = result.scalars().all()
    return [{"id": a.id, "status": a.status.value, "created_at": a.created_at.isoformat()} for a in analyses]


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
        "report": analysis.report,
    }


@router.delete("/{analysis_id}")
async def delete_analysis(analysis_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    """분석 작업을 삭제합니다."""
    analysis = await db.get(Analysis, analysis_id)
    if not analysis:
        raise HTTPException(status_code=404, detail="분석 작업을 찾을 수 없습니다.")
    await db.delete(analysis)
    await db.commit()
    return {"detail": "삭제되었습니다."}
