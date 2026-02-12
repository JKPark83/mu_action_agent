"""PDF 텍스트 추출 도구 - pdfplumber 기반 텍스트/테이블 추출 + OCR 폴백"""

from __future__ import annotations

import logging

import pdfplumber

logger = logging.getLogger(__name__)


async def extract_text_from_pdf(file_path: str) -> tuple[str, list[list[list[str | None]]]]:
    """PDF에서 텍스트와 테이블을 추출한다.

    1차: pdfplumber로 디지털 텍스트 + 테이블 추출
    2차: 텍스트가 50자 미만이면 OCR 폴백 시도

    Returns:
        (추출된 텍스트, 테이블 목록)
    """
    text = ""
    tables: list[list[list[str | None]]] = []

    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text += page_text + "\n"

            page_tables = page.extract_tables()
            if page_tables:
                tables.extend(page_tables)

    # 텍스트가 너무 짧으면 OCR 시도
    if len(text.strip()) < 50:
        text = await _extract_with_ocr(file_path)

    return text, tables


async def _extract_with_ocr(file_path: str) -> str:
    """스캔된 PDF를 OCR로 텍스트 추출한다."""
    try:
        import pytesseract
        from pdf2image import convert_from_path
    except ImportError:
        logger.warning("pytesseract 또는 pdf2image가 설치되지 않아 OCR을 건너뜁니다.")
        return ""

    try:
        images = convert_from_path(file_path)
        text = ""
        for image in images:
            text += pytesseract.image_to_string(image, lang="kor") + "\n"
        return text
    except Exception:
        logger.exception("OCR 처리 중 오류 발생")
        return ""
