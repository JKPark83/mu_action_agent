"""문서 유형 분류 및 데이터 추출용 LLM 프롬프트 템플릿"""

CLASSIFY_PROMPT = """\
다음 PDF 문서의 텍스트를 보고, 문서 유형을 분류해주세요.

가능한 유형:
- registry: 등기부등본 (단독 문서)
- appraisal: 감정평가서 (단독 문서)
- sale_item: 매각물건명세서 (단독 문서)
- status_report: 현황조사보고서 (단독 문서)
- case_notice: 사건송달내역 (단독 문서)
- auction_summary: 경매 포털 종합 정보 페이지 (탱크옥션, 지지옥션, 굿옥션 등에서 출력/저장한 문서로 등기부, 감정가, 매각물건, 임차인 등 여러 정보가 한 문서에 혼합되어 있는 경우)

판단 기준:
- 문서에 "경매", "매각기일", "최저매각가격", "감정가", "건물등기", "임차인 현황" 등 여러 섹션이 혼합되어 있으면 auction_summary입니다.
- 경매 사이트 URL(tankauction, ggi, goodauction 등)이 포함되어 있으면 auction_summary입니다.
- 단일 공적 문서(등기부등본만, 감정평가서만 등)인 경우에만 해당 유형을 선택하세요.

반드시 아래 JSON 형식으로만 응답해주세요 (다른 텍스트 없이):
{{"document_type": "...", "confidence": 0.0}}

문서 텍스트 (앞부분 2000자):
{text}
"""

REGISTRY_EXTRACTION_PROMPT = """\
다음 문서 텍스트에서 등기부등본 관련 정보를 추출하여 JSON으로 반환해주세요.
문서가 경매 포털 종합 페이지일 수 있으므로, 등기 관련 내용(갑구, 을구, 소유권, 근저당, 가압류 등)을 찾아 추출하세요.

추출 대상:
- property_address: 소재지 (문자열)
- property_type: 부동산 유형 (문자열). 반드시 문서에서 "물건종별", "물건종류", "건물유형", "용도", "대상물건" 등의 키워드를 찾아 정확히 추출하세요. 가능한 값: 아파트, 다세대, 연립, 빌라, 다가구, 단독, 오피스텔, 상가, 토지 등. 등기부에 "집합건물"로 표기된 경우 문서 다른 부분에서 구체적 유형(아파트/다세대/연립/오피스텔)을 반드시 확인하세요.
- area: 전용면적 (㎡, 숫자만, 없으면 null)
- building_name: 아파트/건물 단지명 (예: "래미안역삼", "롯데캐슬", 없으면 null)
- owner: 현 소유자 (문자열, 없으면 null)
- section_a_entries: 갑구 사항 목록 (배열, 각 항목은 아래 구조)
  - order: 순위번호 (정수)
  - right_type: 권리종류 (문자열, 예: 소유권이전, 가압류, 임의경매 등)
  - holder: 권리자 (문자열)
  - amount: 채권액 (정수, 원 단위, 없으면 null)
  - registration_date: 접수일자 (문자열 YYYY-MM-DD, 없으면 null)
- section_b_entries: 을구 사항 목록 (갑구와 동일 구조, 근저당권설정, 전세권설정 등)

주의: 갑(4), 갑(5) 같은 표기는 갑구 항목이고, 을(2), 을(3) 같은 표기는 을구 항목입니다.
반드시 JSON 형식으로만 응답해주세요 (다른 텍스트 없이).

문서 텍스트:
{text}
"""

APPRAISAL_EXTRACTION_PROMPT = """\
다음 문서 텍스트에서 감정평가 관련 정보를 추출하여 JSON으로 반환해주세요.
문서가 경매 포털 종합 페이지일 수 있으므로, 감정가/평가액 관련 내용을 찾아 추출하세요.

추출 대상:
- appraised_value: 감정가 (정수, 원 단위)
- land_value: 토지 평가액 (정수, 원 단위, 없으면 null)
- building_value: 건물 평가액 (정수, 원 단위, 없으면 null)
- land_area: 토지 면적 (숫자, ㎡, 없으면 null. 대지권 면적 사용)
- building_area: 건물 면적 (숫자, ㎡, 없으면 null. 전용면적 사용)

반드시 JSON 형식으로만 응답해주세요 (다른 텍스트 없이).

문서 텍스트:
{text}
"""

STATUS_REPORT_EXTRACTION_PROMPT = """\
다음 문서 텍스트에서 현황조사보고서 관련 정보를 추출하여 JSON으로 반환해주세요.

추출 대상:
- investigation_date: 조사일자 (문자열 YYYY-MM-DD, 없으면 null)
- property_address: 소재지 (문자열)
- current_occupant: 현 점유자 (문자열, 예: 소유자 본인, 임차인 홍길동, 없으면 null)
- occupancy_status: 점유 상태 (문자열, 예: 거주중, 공실, 영업중, 없으면 null)
- building_condition: 건물 상태 (문자열, 예: 양호, 보통, 불량, 없으면 null)
- access_road: 접근도로 상태 (문자열, 없으면 null)
- surroundings: 주변 환경 설명 (문자열, 없으면 null)
- special_notes: 특이사항 목록 (문자열 배열, 없으면 빈 배열)

반드시 JSON 형식으로만 응답해주세요 (다른 텍스트 없이).

문서 텍스트:
{text}
"""

SALE_ITEM_EXTRACTION_PROMPT = """\
다음 문서 텍스트에서 매각물건명세서 관련 정보를 추출하여 JSON으로 반환해주세요.
문서가 경매 포털 종합 페이지일 수 있으므로, 사건번호, 임차인/점유 관계, 특별매각조건 등을 찾아 추출하세요.

추출 대상:
- case_number: 사건번호 (문자열, 예: 2025타경33712)
- property_address: 소재지 (문자열)
- occupancy_info: 점유관계 목록 (배열, 각 항목은 아래 구조)
  - occupant_name: 점유자명 (문자열)
  - occupant_type: 유형 (임차인, 소유자, 기타)
  - deposit: 보증금 (정수, 원 단위, 없으면 null)
  - monthly_rent: 월세 (정수, 원 단위, 없으면 null)
  - move_in_date: 전입일 (문자열 YYYY-MM-DD, 없으면 null)
  - confirmed_date: 확정일자 (문자열 YYYY-MM-DD, 없으면 null. "확정일자", "확정일" 등으로 표기됨)
  - dividend_applied: 배당신청 여부 (boolean, "배당요구", "배당신청", "배당" 키워드가 해당 임차인에 존재하면 true, 아니면 false)
- assumed_rights: 인수할 권리 목록 (문자열 배열)
- special_conditions: 특별매각조건 목록 (문자열 배열)

주의:
- "임차인이 없으며 전부를 소유자가 점유 사용합니다" 같은 문구가 있으면 occupancy_info에 소유자 점유로 기록하세요.
- 임차인 현황 테이블에서 확정일자와 배당여부 컬럼을 반드시 확인하세요.
- 배당요구 여부는 "배당요구종기까지 배당요구를 한" 또는 "배당요구함", "배당신청" 등의 표현으로 판별합니다.
반드시 JSON 형식으로만 응답해주세요 (다른 텍스트 없이).

문서 텍스트:
{text}
"""
