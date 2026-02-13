"""문서 파싱 에이전트 노드 - PDF에서 텍스트 추출 및 문서 분류/구조화"""

from __future__ import annotations

import json
import logging
import re

from anthropic import AsyncAnthropic

from app.agents.prompts.document_prompts import (
    APPRAISAL_EXTRACTION_PROMPT,
    CLASSIFY_PROMPT,
    REGISTRY_EXTRACTION_PROMPT,
    SALE_ITEM_EXTRACTION_PROMPT,
    STATUS_REPORT_EXTRACTION_PROMPT,
)
from app.agents.state import AgentState
from app.agents.tools.pdf_extractor import extract_text_from_pdf
from app.config import settings
from app.schemas.document import (
    AppraisalExtraction,
    OccupancyInfo,
    RegistryExtraction,
    RightEntry,
    SaleItemExtraction,
    StatusReportExtraction,
)

logger = logging.getLogger(__name__)

_client: AsyncAnthropic | None = None


def _get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        _client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


def _fix_json(text: str) -> str:
    """LLM이 생성한 JSON의 흔한 오류를 수정한다."""
    return re.sub(r",\s*([}\]])", r"\1", text)


def _try_parse(raw: str) -> dict:
    """JSON 파싱을 시도하고, 실패하면 흔한 오류를 수정 후 재시도한다."""
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return json.loads(_fix_json(raw))


def _parse_json_response(text: str) -> dict:
    """LLM 응답에서 JSON을 추출한다."""
    # 1. ```json ... ``` 블록
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        return _try_parse(match.group(1).strip())
    # 2. 텍스트 내 첫 번째 { ... } 블록
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        return _try_parse(match.group(0))
    # 3. 전체가 JSON
    return _try_parse(text.strip())


async def _call_llm(prompt: str, max_tokens: int = 4096) -> str:
    """Anthropic Claude API를 호출한다."""
    client = _get_client()
    response = await client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


async def classify_document(text: str) -> tuple[str, float]:
    """문서 유형을 분류한다.

    Returns:
        (document_type, confidence)
    """
    prompt = CLASSIFY_PROMPT.format(text=text[:2000])
    raw = await _call_llm(prompt, max_tokens=200)
    data = _parse_json_response(raw)
    return data["document_type"], float(data.get("confidence", 0.0))


async def extract_registry_data(text: str) -> RegistryExtraction:
    """등기부등본에서 구조화된 데이터를 추출한다."""
    prompt = REGISTRY_EXTRACTION_PROMPT.format(text=text)
    raw = await _call_llm(prompt)
    data = _parse_json_response(raw)

    section_a = [
        RightEntry(
            order=e.get("order", 0),
            right_type=e.get("right_type", ""),
            holder=e.get("holder", ""),
            amount=e.get("amount"),
            registration_date=e.get("registration_date"),
        )
        for e in data.get("section_a_entries", [])
    ]
    section_b = [
        RightEntry(
            order=e.get("order", 0),
            right_type=e.get("right_type", ""),
            holder=e.get("holder", ""),
            amount=e.get("amount"),
            registration_date=e.get("registration_date"),
        )
        for e in data.get("section_b_entries", [])
    ]

    return RegistryExtraction(
        property_address=data.get("property_address", ""),
        property_type=data.get("property_type", ""),
        area=data.get("area"),
        building_name=data.get("building_name"),
        owner=data.get("owner"),
        section_a_entries=section_a,
        section_b_entries=section_b,
    )


async def extract_appraisal_data(text: str) -> AppraisalExtraction:
    """감정평가서에서 구조화된 데이터를 추출한다."""
    prompt = APPRAISAL_EXTRACTION_PROMPT.format(text=text)
    raw = await _call_llm(prompt)
    data = _parse_json_response(raw)

    return AppraisalExtraction(
        appraised_value=int(data.get("appraised_value") or 0),
        land_value=data.get("land_value"),
        building_value=data.get("building_value"),
        land_area=data.get("land_area"),
        building_area=data.get("building_area"),
    )


async def extract_status_report_data(text: str) -> StatusReportExtraction:
    """현황조사보고서에서 구조화된 데이터를 추출한다."""
    prompt = STATUS_REPORT_EXTRACTION_PROMPT.format(text=text)
    raw = await _call_llm(prompt)
    data = _parse_json_response(raw)

    return StatusReportExtraction(
        investigation_date=data.get("investigation_date"),
        property_address=data.get("property_address", ""),
        current_occupant=data.get("current_occupant"),
        occupancy_status=data.get("occupancy_status"),
        building_condition=data.get("building_condition"),
        access_road=data.get("access_road"),
        surroundings=data.get("surroundings"),
        special_notes=data.get("special_notes", []),
    )


async def extract_sale_item_data(text: str) -> SaleItemExtraction:
    """매각물건명세서에서 구조화된 데이터를 추출한다."""
    prompt = SALE_ITEM_EXTRACTION_PROMPT.format(text=text)
    raw = await _call_llm(prompt)
    data = _parse_json_response(raw)

    occupancy = [
        OccupancyInfo(
            occupant_name=o.get("occupant_name", ""),
            occupant_type=o.get("occupant_type", "기타"),
            deposit=o.get("deposit"),
            monthly_rent=o.get("monthly_rent"),
            move_in_date=o.get("move_in_date"),
            confirmed_date=o.get("confirmed_date"),
            dividend_applied=bool(o.get("dividend_applied", False)),
        )
        for o in data.get("occupancy_info", [])
    ]

    return SaleItemExtraction(
        case_number=data.get("case_number", ""),
        property_address=data.get("property_address", ""),
        occupancy_info=occupancy,
        assumed_rights=data.get("assumed_rights", []),
        special_conditions=data.get("special_conditions", []),
    )


async def document_parser_node(state: AgentState) -> dict:
    """문서 파싱 에이전트 노드.

    처리 흐름:
    1. 각 PDF 파일에서 텍스트 추출
    2. 문서 유형 분류
    3. 유형별 LLM 기반 데이터 구조화
    4. 파싱 결과를 partial dict로 반환
    """
    registry: RegistryExtraction | None = None
    appraisal: AppraisalExtraction | None = None
    sale_item: SaleItemExtraction | None = None
    status_report: StatusReportExtraction | None = None
    new_errors: list[str] = []

    for file_path in state["file_paths"]:
        try:
            text, _tables = await extract_text_from_pdf(file_path)
            if not text.strip():
                new_errors.append(f"텍스트 추출 실패: {file_path}")
                continue

            doc_type, confidence = await classify_document(text)
            logger.info("문서 분류: %s (confidence=%.2f) - %s", doc_type, confidence, file_path)

            if doc_type == "auction_summary":
                # 복합문서: 3가지 추출을 모두 시도 (개별 실패 허용)
                logger.info("복합문서 감지 - 등기/감정/매각 정보 통합 추출 시작")
                try:
                    registry = await extract_registry_data(text)
                except Exception as exc:
                    logger.warning("복합문서 등기 추출 실패: %s", exc)
                try:
                    appraisal = await extract_appraisal_data(text)
                except Exception as exc:
                    logger.warning("복합문서 감정 추출 실패: %s", exc)
                try:
                    sale_item = await extract_sale_item_data(text)
                except Exception as exc:
                    logger.warning("복합문서 매각 추출 실패: %s", exc)
                try:
                    status_report = await extract_status_report_data(text)
                except Exception as exc:
                    logger.warning("복합문서 현황조사 추출 실패: %s", exc)
            elif doc_type == "registry":
                registry = await extract_registry_data(text)
            elif doc_type == "appraisal":
                appraisal = await extract_appraisal_data(text)
            elif doc_type == "sale_item":
                sale_item = await extract_sale_item_data(text)
            elif doc_type == "status_report":
                status_report = await extract_status_report_data(text)
            else:
                logger.info("지원하지 않는 문서 유형 건너뜀: %s", doc_type)
        except Exception as exc:
            logger.exception("문서 파싱 오류: %s", file_path)
            new_errors.append(f"문서 파싱 오류 ({file_path}): {exc}")

    result: dict = {
        "registry": registry,
        "appraisal": appraisal,
        "sale_item": sale_item,
        "status_report": status_report,
    }
    if new_errors:
        result["errors"] = new_errors
    return result
