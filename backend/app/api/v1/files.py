"""File upload, retrieval, and deletion endpoints."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.config import settings
from app.models.file import UploadedFile

logger = logging.getLogger("app.files")

router = APIRouter()

MAX_FILE_SIZE = settings.max_file_size_mb * 1024 * 1024  # bytes
ALLOWED_CONTENT_TYPE = "application/pdf"


@router.post("/upload", status_code=201)
async def upload_file(
    analysis_id: str,
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """PDF 파일을 업로드합니다.

    1. MIME 타입 검증 (PDF만 허용)
    2. 파일 크기 검증 (50MB 이하)
    3. uploads/{analysis_id}/ 디렉토리에 UUID 기반 이름으로 저장
    4. DB에 UploadedFile 레코드 생성
    """
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="PDF 파일만 업로드 가능합니다.")

    if file.content_type != ALLOWED_CONTENT_TYPE:
        raise HTTPException(status_code=400, detail="PDF 파일만 업로드 가능합니다.")

    if file.size is not None and file.size > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="파일 크기가 50MB를 초과합니다.")

    upload_dir = Path(settings.upload_dir) / analysis_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_id = str(uuid4())
    suffix = Path(file.filename).suffix  # .pdf
    stored_name = f"{file_id}{suffix}"
    stored_path = upload_dir / stored_name

    with open(stored_path, "wb") as buf:
        shutil.copyfileobj(file.file, buf)

    file_size = stored_path.stat().st_size

    if file_size > MAX_FILE_SIZE:
        stored_path.unlink(missing_ok=True)
        raise HTTPException(status_code=413, detail="파일 크기가 50MB를 초과합니다.")

    uploaded = UploadedFile(
        id=file_id,
        analysis_id=analysis_id,
        filename=file.filename,
        stored_path=str(stored_path),
        file_size=file_size,
    )
    db.add(uploaded)
    await db.commit()
    await db.refresh(uploaded)

    logger.debug("uploaded file: id=%s name=%s size=%d", file_id, file.filename, file_size)
    return {"id": uploaded.id, "filename": uploaded.filename}


@router.get("/{file_id}")
async def get_file(file_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    """파일 정보를 조회합니다."""
    uploaded = await db.get(UploadedFile, file_id)
    if not uploaded:
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
    return {
        "id": uploaded.id,
        "filename": uploaded.filename,
        "file_size": uploaded.file_size,
        "document_type": uploaded.document_type,
    }


@router.delete("/{file_id}")
async def delete_file(file_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    """파일을 삭제합니다 (DB + 디스크)."""
    uploaded = await db.get(UploadedFile, file_id)
    if not uploaded:
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")

    stored_path = Path(uploaded.stored_path)
    if stored_path.exists():
        stored_path.unlink()
        logger.debug("deleted disk file: %s", stored_path)

    await db.delete(uploaded)
    await db.commit()
    return {"detail": "삭제되었습니다."}
