"""문서 유형 분류 및 데이터 추출용 LLM 프롬프트 템플릿"""

CLASSIFY_PROMPT = """\
다음 PDF 문서의 텍스트를 보고, 문서 유형을 분류해주세요.

가능한 유형:
- registry: 등기부등본
- appraisal: 감정평가서
- sale_item: 매각물건명세서
- status_report: 현황조사보고서
- case_notice: 사건송달내역

반드시 아래 JSON 형식으로만 응답해주세요 (다른 텍스트 없이):
{{"document_type": "...", "confidence": 0.0}}

문서 텍스트 (앞부분 2000자):
{text}
"""

REGISTRY_EXTRACTION_PROMPT = """\
다음 등기부등본 텍스트에서 아래 정보를 추출하여 JSON으로 반환해주세요.

추출 대상:
- property_address: 소재지 (문자열)
- property_type: 부동산 유형 (문자열)
- area: 면적 (㎡, 숫자만, 없으면 null)
- owner: 현 소유자 (문자열, 없으면 null)
- section_a_entries: 갑구 사항 목록 (배열, 각 항목은 아래 구조)
  - order: 순위번호 (정수)
  - right_type: 권리종류 (문자열)
  - holder: 권리자 (문자열)
  - amount: 채권액 (정수, 원 단위, 없으면 null)
  - registration_date: 접수일자 (문자열 YYYY-MM-DD, 없으면 null)
- section_b_entries: 을구 사항 목록 (갑구와 동일 구조)

반드시 JSON 형식으로만 응답해주세요 (다른 텍스트 없이).

문서 텍스트:
{text}
"""

APPRAISAL_EXTRACTION_PROMPT = """\
다음 감정평가서 텍스트에서 아래 정보를 추출하여 JSON으로 반환해주세요.

추출 대상:
- appraised_value: 감정가 (정수, 원 단위)
- land_value: 토지 평가액 (정수, 원 단위, 없으면 null)
- building_value: 건물 평가액 (정수, 원 단위, 없으면 null)
- land_area: 토지 면적 (숫자, ㎡, 없으면 null)
- building_area: 건물 면적 (숫자, ㎡, 없으면 null)

반드시 JSON 형식으로만 응답해주세요 (다른 텍스트 없이).

문서 텍스트:
{text}
"""

SALE_ITEM_EXTRACTION_PROMPT = """\
다음 매각물건명세서 텍스트에서 아래 정보를 추출하여 JSON으로 반환해주세요.

추출 대상:
- case_number: 사건번호 (문자열)
- property_address: 소재지 (문자열)
- occupancy_info: 점유관계 목록 (배열, 각 항목은 아래 구조)
  - occupant_name: 점유자명 (문자열)
  - occupant_type: 유형 (임차인, 소유자, 기타)
  - deposit: 보증금 (정수, 원 단위, 없으면 null)
  - monthly_rent: 월세 (정수, 원 단위, 없으면 null)
  - move_in_date: 전입일 (문자열 YYYY-MM-DD, 없으면 null)
- assumed_rights: 인수할 권리 목록 (문자열 배열)
- special_conditions: 특별매각조건 목록 (문자열 배열)

반드시 JSON 형식으로만 응답해주세요 (다른 텍스트 없이).

문서 텍스트:
{text}
"""
