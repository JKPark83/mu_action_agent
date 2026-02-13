"""Task-01: 경매 문서 파싱 단위 테스트

LLM 호출은 모두 mock 처리하여 외부 의존성 없이 테스트한다.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.agents.nodes.document_parser import (
    _parse_json_response,
    classify_document,
    document_parser_node,
    extract_appraisal_data,
    extract_registry_data,
    extract_sale_item_data,
)
from app.agents.state import AgentState
from app.agents.tools.pdf_extractor import extract_text_from_pdf
from app.schemas.document import AppraisalExtraction, RegistryExtraction, SaleItemExtraction


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_registry_text() -> str:
    return """
    부동산등기부등본(말소사항포함)
    [표제부]
    소재지: 서울특별시 강남구 역삼동 123-45
    건물유형: 아파트
    면적: 84.99㎡

    [갑구]
    1. 소유권이전 2020-01-15 홍길동
    2. 가압류 2023-05-10 주식회사 좋은은행 50,000,000원

    [을구]
    1. 근저당권설정 2020-02-01 주식회사 좋은은행 200,000,000원
    """


@pytest.fixture
def sample_appraisal_text() -> str:
    return """
    감정평가서
    감정가: 350,000,000원
    토지평가액: 200,000,000원
    건물평가액: 150,000,000원
    토지면적: 50.5㎡
    건물면적: 84.99㎡
    """


@pytest.fixture
def sample_sale_item_text() -> str:
    return """
    매각물건명세서
    사건번호: 2023타경12345
    소재지: 서울특별시 강남구 역삼동 123-45
    점유관계: 임차인 김철수, 보증금 100,000,000원, 월세 500,000원
    인수할 권리: 선순위 전세권
    """


# ---------------------------------------------------------------------------
# T-1: PDF 텍스트 추출 (디지털 PDF)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_text_digital_pdf():
    """디지털 PDF에서 텍스트를 추출할 수 있다."""
    expected_text = "등기부등본 서울시 강남구 역삼동 123-45 테스트 문서입니다. 소유권이전 근저당권설정 충분히 긴 텍스트를 포함합니다. 갑구 을구 사항이 기록되어 있습니다."
    mock_page = MagicMock()
    mock_page.extract_text.return_value = expected_text
    mock_page.extract_tables.return_value = [["col1", "col2"]]

    with patch("app.agents.tools.pdf_extractor.pdfplumber") as mock_pdfplumber:
        # MagicMock의 context manager 체인을 따라감:
        # pdfplumber.open(path) -> return_value -> __enter__() -> return_value
        mock_pdfplumber.open.return_value.__enter__.return_value.pages = [mock_page]
        text, tables = await extract_text_from_pdf("/fake/path.pdf")

    assert len(text.strip()) > 50
    assert "등기부등본" in text
    assert isinstance(tables, list)
    assert len(tables) == 1


# ---------------------------------------------------------------------------
# T-2: 문서 분류 (등기부등본)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_classify_registry(sample_registry_text: str):
    """등기부등본 텍스트를 registry로 분류한다."""
    mock_response = json.dumps({"document_type": "registry", "confidence": 0.95})

    with patch("app.agents.nodes.document_parser._call_llm", new_callable=AsyncMock, return_value=mock_response):
        doc_type, confidence = await classify_document(sample_registry_text)

    assert doc_type == "registry"
    assert confidence == pytest.approx(0.95)


# ---------------------------------------------------------------------------
# T-3: 문서 분류 (감정평가서)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_classify_appraisal(sample_appraisal_text: str):
    """감정평가서 텍스트를 appraisal로 분류한다."""
    mock_response = json.dumps({"document_type": "appraisal", "confidence": 0.92})

    with patch("app.agents.nodes.document_parser._call_llm", new_callable=AsyncMock, return_value=mock_response):
        doc_type, confidence = await classify_document(sample_appraisal_text)

    assert doc_type == "appraisal"
    assert confidence == pytest.approx(0.92)


# ---------------------------------------------------------------------------
# T-4: 등기부 데이터 구조화
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_extract_registry_data(sample_registry_text: str):
    """등기부등본에서 갑구/을구를 포함한 구조화 데이터를 추출한다."""
    mock_response = json.dumps({
        "property_address": "서울특별시 강남구 역삼동 123-45",
        "property_type": "아파트",
        "area": 84.99,
        "owner": "홍길동",
        "section_a_entries": [
            {
                "order": 1,
                "right_type": "소유권이전",
                "holder": "홍길동",
                "amount": None,
                "registration_date": "2020-01-15",
            },
            {
                "order": 2,
                "right_type": "가압류",
                "holder": "주식회사 좋은은행",
                "amount": 50000000,
                "registration_date": "2023-05-10",
            },
        ],
        "section_b_entries": [
            {
                "order": 1,
                "right_type": "근저당권설정",
                "holder": "주식회사 좋은은행",
                "amount": 200000000,
                "registration_date": "2020-02-01",
            },
        ],
    })

    with patch("app.agents.nodes.document_parser._call_llm", new_callable=AsyncMock, return_value=mock_response):
        result = await extract_registry_data(sample_registry_text)

    assert isinstance(result, RegistryExtraction)
    assert result.property_address == "서울특별시 강남구 역삼동 123-45"
    assert result.property_type == "아파트"
    assert result.area == pytest.approx(84.99)
    assert result.owner == "홍길동"
    assert len(result.section_a_entries) == 2
    assert result.section_a_entries[1].right_type == "가압류"
    assert result.section_a_entries[1].amount == 50000000
    assert len(result.section_b_entries) == 1
    assert result.section_b_entries[0].amount == 200000000


# ---------------------------------------------------------------------------
# T-5: 노드 전체 흐름
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_document_parser_node():
    """document_parser_node가 state에 파싱 결과를 저장한다."""
    state: AgentState = {
        "analysis_id": "test-123",
        "file_paths": ["/fake/registry.pdf", "/fake/appraisal.pdf"],
    }

    # PDF 추출 mock
    async def mock_extract(file_path: str):
        if "registry" in file_path:
            return "등기부등본 서울시 강남구 역삼동 충분히 긴 텍스트입니다. 갑구 을구 소유권이전.", []
        return "감정평가서 감정가 350000000원 토지평가액 건물평가액 토지면적 건물면적.", []

    # 분류 mock
    async def mock_classify(text: str):
        if "등기부등본" in text:
            return "registry", 0.95
        return "appraisal", 0.90

    # 추출 mock
    mock_registry = RegistryExtraction(
        property_address="서울시 강남구",
        property_type="아파트",
        area=84.99,
        owner="홍길동",
    )
    mock_appraisal = AppraisalExtraction(appraised_value=350000000)

    with (
        patch("app.agents.nodes.document_parser.extract_text_from_pdf", side_effect=mock_extract),
        patch("app.agents.nodes.document_parser.classify_document", side_effect=mock_classify),
        patch(
            "app.agents.nodes.document_parser.extract_registry_data",
            new_callable=AsyncMock,
            return_value=mock_registry,
        ),
        patch(
            "app.agents.nodes.document_parser.extract_appraisal_data",
            new_callable=AsyncMock,
            return_value=mock_appraisal,
        ),
    ):
        result = await document_parser_node(state)

    assert result["registry"] is not None
    assert result["registry"].property_address == "서울시 강남구"
    assert result["appraisal"] is not None
    assert result["appraisal"].appraised_value == 350000000
    assert len(result.get("errors", [])) == 0


# ---------------------------------------------------------------------------
# 유틸리티 테스트
# ---------------------------------------------------------------------------


def test_parse_json_response_plain():
    """순수 JSON 텍스트를 파싱한다."""
    raw = '{"document_type": "registry", "confidence": 0.9}'
    result = _parse_json_response(raw)
    assert result["document_type"] == "registry"


def test_parse_json_response_code_block():
    """```json 코드 블록에서 JSON을 추출한다."""
    raw = '```json\n{"document_type": "appraisal", "confidence": 0.85}\n```'
    result = _parse_json_response(raw)
    assert result["document_type"] == "appraisal"


@pytest.mark.asyncio
async def test_document_parser_node_handles_extraction_error():
    """파싱 중 오류가 발생하면 errors에 기록하고 계속 진행한다."""
    state: AgentState = {
        "analysis_id": "test-err",
        "file_paths": ["/fake/broken.pdf"],
    }

    with patch(
        "app.agents.nodes.document_parser.extract_text_from_pdf",
        new_callable=AsyncMock,
        side_effect=Exception("PDF 손상"),
    ):
        result = await document_parser_node(state)

    assert len(result.get("errors", [])) == 1
    assert "PDF 손상" in result["errors"][0]
    assert result["registry"] is None


# ---------------------------------------------------------------------------
# T-6: 복합문서 (auction_summary) 노드 전체 흐름
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_document_parser_node_auction_summary():
    """auction_summary로 분류된 복합문서에서 등기/감정/매각 3가지를 모두 추출한다."""
    state: AgentState = {
        "analysis_id": "test-auction",
        "file_paths": ["/fake/tankauction.pdf"],
    }

    # PDF 추출 mock - 탱크옥션 종합 페이지 텍스트
    async def mock_extract(file_path: str):
        return "경매 2025타경33712 매각기일 감정가 546000000 건물등기 임차인 현황 tankauction", []

    # 분류 mock - auction_summary로 분류
    async def mock_classify(text: str):
        return "auction_summary", 0.93

    # 추출 mock
    mock_registry = RegistryExtraction(
        property_address="경기도 김포시 운양동 1301-1 한강신도시롯데캐슬 301동 6층 601호",
        property_type="아파트",
        area=84.9823,
        owner="윤미라",
    )
    mock_appraisal = AppraisalExtraction(
        appraised_value=546000000,
        land_value=273000000,
        building_value=273000000,
        land_area=50.7099,
        building_area=84.9823,
    )
    mock_sale_item = SaleItemExtraction(
        case_number="2025타경33712",
        property_address="경기도 김포시 운양동 1301-1",
    )

    with (
        patch("app.agents.nodes.document_parser.extract_text_from_pdf", side_effect=mock_extract),
        patch("app.agents.nodes.document_parser.classify_document", side_effect=mock_classify),
        patch(
            "app.agents.nodes.document_parser.extract_registry_data",
            new_callable=AsyncMock,
            return_value=mock_registry,
        ),
        patch(
            "app.agents.nodes.document_parser.extract_appraisal_data",
            new_callable=AsyncMock,
            return_value=mock_appraisal,
        ),
        patch(
            "app.agents.nodes.document_parser.extract_sale_item_data",
            new_callable=AsyncMock,
            return_value=mock_sale_item,
        ),
    ):
        result = await document_parser_node(state)

    # 3가지 모두 추출되어야 함
    assert result["registry"] is not None
    assert result["registry"].property_address == "경기도 김포시 운양동 1301-1 한강신도시롯데캐슬 301동 6층 601호"
    assert result["registry"].area == pytest.approx(84.9823)
    assert result["appraisal"] is not None
    assert result["appraisal"].appraised_value == 546000000
    assert result["sale_item"] is not None
    assert result["sale_item"].case_number == "2025타경33712"
    assert len(result.get("errors", [])) == 0


@pytest.mark.asyncio
async def test_document_parser_node_auction_summary_partial_failure():
    """auction_summary에서 일부 추출이 실패해도 나머지는 정상 추출한다."""
    state: AgentState = {
        "analysis_id": "test-auction-partial",
        "file_paths": ["/fake/tankauction.pdf"],
    }

    async def mock_extract(file_path: str):
        return "경매 2025타경33712 매각기일 감정가 건물등기 임차인 현황 tankauction", []

    async def mock_classify(text: str):
        return "auction_summary", 0.90

    mock_registry = RegistryExtraction(
        property_address="경기도 김포시 운양동",
        property_type="아파트",
        area=84.98,
    )
    mock_appraisal = AppraisalExtraction(appraised_value=546000000)

    with (
        patch("app.agents.nodes.document_parser.extract_text_from_pdf", side_effect=mock_extract),
        patch("app.agents.nodes.document_parser.classify_document", side_effect=mock_classify),
        patch(
            "app.agents.nodes.document_parser.extract_registry_data",
            new_callable=AsyncMock,
            return_value=mock_registry,
        ),
        patch(
            "app.agents.nodes.document_parser.extract_appraisal_data",
            new_callable=AsyncMock,
            return_value=mock_appraisal,
        ),
        patch(
            "app.agents.nodes.document_parser.extract_sale_item_data",
            new_callable=AsyncMock,
            side_effect=Exception("매각물건 추출 실패"),
        ),
    ):
        result = await document_parser_node(state)

    # 등기/감정은 성공, 매각은 실패해도 에러 없이 진행
    assert result["registry"] is not None
    assert result["appraisal"] is not None
    assert result["sale_item"] is None
    assert len(result.get("errors", [])) == 0  # 개별 추출 실패는 warning 로그만, errors에 추가하지 않음
