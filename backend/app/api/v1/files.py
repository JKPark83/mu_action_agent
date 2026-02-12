from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db
from app.models.file import UploadedFile

router = APIRouter()


@router.post("/upload")
async def upload_file(
    analysis_id: str,
    file: UploadFile,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """PDF 파일을 업로드합니다."""
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="PDF 파일만 업로드할 수 있습니다.")

    # TODO: 파일 저장 로직 구현
    uploaded = UploadedFile(
        analysis_id=analysis_id,
        filename=file.filename,
        stored_path="",  # TODO
        file_size=0,  # TODO
    )
    db.add(uploaded)
    await db.commit()
    await db.refresh(uploaded)
    return {"id": uploaded.id, "filename": uploaded.filename}


@router.get("/{file_id}")
async def get_file(file_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    """파일 정보를 조회합니다."""
    uploaded = await db.get(UploadedFile, file_id)
    if not uploaded:
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
    return {"id": uploaded.id, "filename": uploaded.filename, "document_type": uploaded.document_type}


@router.delete("/{file_id}")
async def delete_file(file_id: str, db: AsyncSession = Depends(get_db)) -> dict:
    """파일을 삭제합니다."""
    uploaded = await db.get(UploadedFile, file_id)
    if not uploaded:
        raise HTTPException(status_code=404, detail="파일을 찾을 수 없습니다.")
    await db.delete(uploaded)
    await db.commit()
    return {"detail": "삭제되었습니다."}
