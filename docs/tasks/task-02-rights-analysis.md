# Task-02: 권리분석 에이전트 구현

> **참조 스펙**: PRD-02 전체
> **예상 작업 시간**: 6~8시간
> **선행 작업**: Task-01 (문서 파싱 - 등기부등본/매각물건명세서 파싱 결과 필요)
> **변경 파일 수**: 3~4개

---

## 목차

1. [말소기준권리 판단 로직](#1-말소기준권리-판단-로직)
2. [권리 인수/소멸 판별](#2-권리-인수소멸-판별)
3. [임차인 분석](#3-임차인-분석)
4. [에이전트 노드 구현](#4-에이전트-노드-구현)
5. [테스트 가이드](#5-테스트-가이드)

---

## 1. 말소기준권리 판단 로직

### 1.1 판단 기준

> 참조 스키마: `backend/app/schemas/rights.py`

말소기준권리는 경매신청의 원인이 된 권리 중 가장 선순위 권리를 의미합니다.

```python
# 말소기준권리가 될 수 있는 권리 유형
EXTINGUISHMENT_ELIGIBLE_TYPES = [
    "근저당권",
    "전세권",
    "가압류",
    "담보가등기",
    "압류",
    "경매기입등기",
]

def determine_extinguishment_basis(
    section_a_entries: list[RightEntry],
    section_b_entries: list[RightEntry],
) -> ExtinguishmentBasis:
    """
    1. 갑구+을구의 모든 권리를 접수일자순으로 정렬
    2. 말소기준권리 대상 유형만 필터링
    3. 가장 먼저 설정된 권리를 말소기준권리로 결정
    """
    all_entries = section_a_entries + section_b_entries
    eligible = [e for e in all_entries if e.right_type in EXTINGUISHMENT_ELIGIBLE_TYPES]
    eligible.sort(key=lambda e: e.registration_date)

    basis = eligible[0] if eligible else None
    # ExtinguishmentBasis 객체 반환
```

---

## 2. 권리 인수/소멸 판별

### 2.1 판별 로직

```python
def classify_rights(
    all_entries: list[RightEntry],
    basis_date: date,
) -> tuple[list[AnalyzedRight], list[AnalyzedRight]]:
    """
    말소기준권리 설정일을 기준으로:
    - 이전에 설정된 권리 → 인수 가능성 판단
    - 이후에 설정된 권리 → 소멸
    """
    assumed = []
    extinguished = []

    for entry in all_entries:
        if entry.registration_date < basis_date:
            # 선순위: 유형별 인수 여부 세부 판단
            status = analyze_prior_right(entry)
        else:
            status = "소멸"

        analyzed = AnalyzedRight(
            order=entry.order,
            right_type=entry.right_type,
            registration_date=entry.registration_date,
            right_holder=entry.right_holder,
            amount=entry.amount,
            status=status,
            analysis_note="...",
        )
        if status == "인수":
            assumed.append(analyzed)
        else:
            extinguished.append(analyzed)

    return assumed, extinguished
```

### 2.2 Claude 활용: 복잡한 권리 해석

특수 권리(가처분, 유치권, 법정지상권 등)는 Claude에게 판단을 위임합니다.

```python
RIGHTS_ANALYSIS_PROMPT = """
당신은 대한민국 부동산 경매 권리분석 전문가입니다.

다음 등기부등본 정보를 분석하여:
1. 말소기준권리를 판단하세요
2. 각 권리의 인수/소멸 여부를 판단하세요
3. 특수 위험(가처분, 유치권, 법정지상권)이 있는지 확인하세요
4. 종합 위험도를 상/중/하로 평가하세요

갑구 사항: {section_a}
을구 사항: {section_b}
매각물건명세서 점유관계: {occupancy}

JSON 형식으로 응답하세요.
"""
```

---

## 3. 임차인 분석

### 3.1 대항력 판단

```python
def analyze_tenant(
    tenant: OccupancyInfo,
    basis_date: date,
) -> TenantAnalysis:
    """
    대항력 유무 판단:
    - 전입신고일 + 확정일자가 말소기준권리보다 선순위 → 대항력 있음
    - 소액임차인 최우선변제권 별도 확인
    """
    has_opposition = (
        tenant.move_in_date is not None
        and tenant.move_in_date < basis_date
    )

    return TenantAnalysis(
        tenant_name=tenant.occupant,
        deposit=tenant.lease_deposit or 0,
        monthly_rent=tenant.monthly_rent or 0,
        move_in_date=tenant.move_in_date,
        has_opposition_right=has_opposition,
        has_priority_repayment=check_priority_repayment(tenant),
        expected_dividend=0,  # 배당 예측 로직
        eviction_difficulty=estimate_eviction_difficulty(tenant, has_opposition),
        analysis_note="",
    )
```

### 3.2 명도 난이도 추정

```python
def estimate_eviction_difficulty(
    tenant: OccupancyInfo,
    has_opposition: bool,
) -> str:
    """
    명도 난이도: 상/중/하
    - 대항력 있음 + 보증금 큼 → 상
    - 대항력 있음 + 보증금 작음 → 중
    - 대항력 없음 → 하
    """
```

---

## 4. 에이전트 노드 구현

### 4.1 rights_analysis 노드

> 파일: `backend/app/agents/nodes/rights_analysis.py`

```python
async def rights_analysis_node(state: AgentState) -> AgentState:
    """
    처리 흐름:
    1. state에서 등기부등본 + 매각물건명세서 파싱 결과 가져오기
    2. 말소기준권리 판단
    3. 각 권리 인수/소멸 분류
    4. 임차인 분석
    5. Claude로 복잡한 권리 해석 + 위험도 종합 평가
    6. RightsAnalysisResult 생성하여 state에 저장
    """
    registry = state.get("registry")
    sale_item = state.get("sale_item")

    if not registry:
        return {**state, "rights_analysis": None, "errors": state.get("errors", []) + ["등기부등본 파싱 결과 없음"]}

    # 말소기준권리 판단
    basis = determine_extinguishment_basis(
        registry.section_a_entries,
        registry.section_b_entries,
    )

    # 권리 분류
    assumed, extinguished = classify_rights(
        registry.section_a_entries + registry.section_b_entries,
        basis.registration_date,
    )

    # 임차인 분석
    tenants = []
    if sale_item and sale_item.occupancy_info:
        for occ in sale_item.occupancy_info:
            tenants.append(analyze_tenant(occ, basis.registration_date))

    # Claude 종합 분석 (위험도, 분석 근거, 경고사항)
    claude_result = await analyze_with_claude(registry, sale_item, basis, assumed)

    result = RightsAnalysisResult(
        case_number=sale_item.case_number if sale_item else "",
        extinguishment_basis=basis,
        all_rights=assumed + extinguished,
        assumed_rights=assumed,
        extinguished_rights=extinguished,
        tenants=tenants,
        risk_level=claude_result["risk_level"],
        risk_factors=claude_result["risk_factors"],
        total_assumed_amount=sum(r.amount or 0 for r in assumed),
        analysis_reasoning=claude_result["reasoning"],
        confidence_score=claude_result["confidence"],
        warnings=claude_result["warnings"],
    )

    return {**state, "rights_analysis": result}
```

---

## 5. 테스트 가이드

### 5.1 테스트 케이스

| ID | 테스트명 | 설명 | 기대 결과 |
|:---:|:---|:---|:---|
| T-1 | `test_extinguishment_basis_basic` | 근저당 1건 → 말소기준 | 해당 근저당이 기준 |
| T-2 | `test_extinguishment_basis_multiple` | 근저당+가압류 → 선순위 판단 | 먼저 설정된 것이 기준 |
| T-3 | `test_classify_prior_right_assumed` | 선순위 전세권 | 인수 판정 |
| T-4 | `test_classify_post_right_extinguished` | 후순위 근저당 | 소멸 판정 |
| T-5 | `test_tenant_with_opposition` | 대항력 있는 임차인 | has_opposition_right=True |
| T-6 | `test_tenant_without_opposition` | 대항력 없는 임차인 | has_opposition_right=False |
| T-7 | `test_rights_analysis_node_no_registry` | 등기부 없는 경우 | 에러 메시지 추가 |

### 5.2 테스트 실행

```bash
cd backend
uv run pytest tests/unit/agents/test_rights_analysis.py -v
```

---

## 파일 변경 요약

### 수정 파일

| 파일 경로 | 변경 내용 |
|:---|:---|
| `backend/app/agents/nodes/rights_analysis.py` | 권리분석 노드 전체 구현 |

### 신규 생성 파일

| 파일 경로 | 설명 |
|:---|:---|
| `backend/app/agents/prompts/rights_prompts.py` | 권리분석 LLM 프롬프트 |
| `backend/tests/unit/agents/test_rights_analysis.py` | 단위 테스트 |
