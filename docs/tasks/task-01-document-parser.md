# Task-01: 경매 문서 파싱 구현

> **참조 스펙**: PRD-01 전체
> **예상 작업 시간**: 6~8시간
> **선행 작업**: Task-00 (파일 업로드)
> **변경 파일 수**: 4~5개

---

## 목차

1. [PDF 텍스트 추출 도구](#1-pdf-텍스트-추출-도구)
2. [문서 유형 분류](#2-문서-유형-분류)
3. [LLM 기반 데이터 구조화](#3-llm-기반-데이터-구조화)
4. [에이전트 노드 구현](#4-에이전트-노드-구현)
5. [테스트 가이드](#5-테스트-가이드)

---

## 1. PDF 텍스트 추출 도구

### 1.1 pdf_extractor 구현

> 파일: `backend/app/agents/tools/pdf_extractor.py`

```python
import pdfplumber
from pypdf2 import PdfReader

async def extract_text_from_pdf(file_path: str) -> str:
    """
    1차: pdfplumber로 텍스트 + 테이블 추출 시도
    2차: 텍스트가 비어있으면 OCR 처리 (pytesseract)
    """
    text = ""
    tables = []

    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text() or ""
            text += page_text + "\n"

            page_tables = page.extract_tables()
            if page_tables:
                tables.extend(page_tables)

    # 텍스트가 너무 짧으면 OCR 시도
    if len(text.strip()) < 50:
        text = await extract_with_ocr(file_path)

    return text, tables
```

### 1.2 OCR 처리

```python
import pytesseract
from PIL import Image
from pdf2image import convert_from_path

async def extract_with_ocr(file_path: str) -> str:
    """스캔된 PDF를 OCR로 텍스트 추출"""
    images = convert_from_path(file_path)
    text = ""
    for image in images:
        text += pytesseract.image_to_string(image, lang="kor") + "\n"
    return text
```

---

## 2. 문서 유형 분류

### 2.1 Claude를 활용한 문서 분류

> 파일: `backend/app/agents/tools/pdf_extractor.py` (또는 별도 파일)

```python
from anthropic import Anthropic

CLASSIFY_PROMPT = """
다음 PDF 문서의 텍스트를 보고, 문서 유형을 분류해주세요.

가능한 유형:
- registry: 등기부등본
- appraisal: 감정평가서
- sale_item: 매각물건명세서
- status_report: 현황조사보고서
- case_notice: 사건송달내역

JSON으로 응답해주세요:
{{"document_type": "...", "confidence": 0.0~1.0}}

문서 텍스트 (앞부분 2000자):
{text}
"""

async def classify_document(text: str) -> tuple[str, float]:
    client = Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=200,
        messages=[{"role": "user", "content": CLASSIFY_PROMPT.format(text=text[:2000])}],
    )
    # JSON 파싱 후 (document_type, confidence) 반환
```

---

## 3. LLM 기반 데이터 구조화

### 3.1 등기부등본 데이터 추출

```python
REGISTRY_EXTRACTION_PROMPT = """
다음 등기부등본 텍스트에서 아래 정보를 추출하여 JSON으로 반환해주세요.

추출 대상:
- property_address: 소재지
- property_type: 부동산 유형
- area: 면적 (㎡, 숫자만)
- owner: 현 소유자
- section_a_entries: 갑구 사항 목록 (순위번호, 접수일자, 권리종류, 권리자, 채권액, 상세내용)
- section_b_entries: 을구 사항 목록 (동일 구조)

문서 텍스트:
{text}
"""
```

### 3.2 감정평가서 데이터 추출

```python
APPRAISAL_EXTRACTION_PROMPT = """
감정평가서에서 추출:
- appraised_value: 감정가 (원, 숫자만)
- appraisal_date: 감정일 (YYYY-MM-DD)
- land_value / building_value: 토지/건물 평가액
- land_area / building_area: 토지/건물 면적
- official_land_price: 개별공시지가
"""
```

### 3.3 매각물건명세서 데이터 추출

```python
SALE_ITEM_EXTRACTION_PROMPT = """
매각물건명세서에서 추출:
- case_number: 사건번호
- property_address: 소재지
- occupancy_info: 점유관계 (점유자, 유형, 보증금, 월세, 전입일, 대항력)
- assumed_rights: 인수할 권리
- special_conditions: 특별매각조건
"""
```

---

## 4. 에이전트 노드 구현

### 4.1 document_parser 노드

> 파일: `backend/app/agents/nodes/document_parser.py`
> 참조 스키마: `backend/app/schemas/document.py`

```python
from app.agents.state import AgentState
from app.agents.tools.pdf_extractor import extract_text_from_pdf, classify_document

async def document_parser_node(state: AgentState) -> AgentState:
    """
    처리 흐름:
    1. 각 PDF 파일에서 텍스트 추출
    2. 문서 유형 분류
    3. 유형별 LLM 기반 데이터 구조화
    4. 파싱 결과를 state에 저장
    """
    parsed = {}

    for file_path in state["file_paths"]:
        text, tables = await extract_text_from_pdf(file_path)
        doc_type, confidence = await classify_document(text)

        if doc_type == "registry":
            parsed["registry"] = await extract_registry_data(text)
        elif doc_type == "appraisal":
            parsed["appraisal"] = await extract_appraisal_data(text)
        elif doc_type == "sale_item":
            parsed["sale_item"] = await extract_sale_item_data(text)

    return {
        **state,
        "registry": parsed.get("registry"),
        "appraisal": parsed.get("appraisal"),
        "sale_item": parsed.get("sale_item"),
    }
```

---

## 5. 테스트 가이드

### 5.1 테스트 케이스

| ID | 테스트명 | 설명 | 기대 결과 |
|:---:|:---|:---|:---|
| T-1 | `test_extract_text_digital_pdf` | 디지털 PDF 텍스트 추출 | 텍스트 반환 |
| T-2 | `test_classify_registry` | 등기부등본 분류 | document_type="registry" |
| T-3 | `test_classify_appraisal` | 감정평가서 분류 | document_type="appraisal" |
| T-4 | `test_extract_registry_data` | 등기부 데이터 구조화 | 갑구/을구 파싱 확인 |
| T-5 | `test_document_parser_node` | 노드 전체 흐름 | state에 파싱 결과 저장 |

### 5.2 테스트 실행

```bash
cd backend
uv run pytest tests/unit/agents/test_document_parser.py -v
```

---

## 파일 변경 요약

### 수정 파일

| 파일 경로 | 변경 내용 |
|:---|:---|
| `backend/app/agents/tools/pdf_extractor.py` | 텍스트 추출 + OCR + 문서 분류 구현 |
| `backend/app/agents/nodes/document_parser.py` | 파싱 노드 전체 구현 |

### 신규 생성 파일

| 파일 경로 | 설명 |
|:---|:---|
| `backend/app/agents/prompts/document_prompts.py` | 문서별 LLM 프롬프트 템플릿 |
| `backend/tests/unit/agents/test_document_parser.py` | 단위 테스트 |
