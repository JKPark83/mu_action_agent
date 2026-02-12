"""권리분석 에이전트 노드 - 말소기준권리, 인수권리, 임차인 분석"""

from __future__ import annotations

import json
import logging
import re

from anthropic import AsyncAnthropic

from app.agents.prompts.rights_prompts import RIGHTS_ANALYSIS_PROMPT
from app.agents.state import AgentState
from app.config import settings
from app.schemas.document import OccupancyInfo, RightEntry
from app.schemas.rights import RightsAnalysisResult, RiskLevel, TenantAnalysis

logger = logging.getLogger(__name__)

# 말소기준권리가 될 수 있는 권리 유형
EXTINGUISHMENT_ELIGIBLE_TYPES = [
    "근저당권",
    "근저당권설정",
    "전세권",
    "전세권설정",
    "가압류",
    "담보가등기",
    "압류",
    "경매기입등기",
]

# 소액임차인 최우선변제 기준 (서울 기준, 원)
SMALL_DEPOSIT_THRESHOLD = 165_000_000

_client: AsyncAnthropic | None = None


def _get_client() -> AsyncAnthropic:
    global _client
    if _client is None:
        _client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client


def _parse_json_response(text: str) -> dict:
    """LLM 응답에서 JSON을 추출한다."""
    match = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if match:
        return json.loads(match.group(1).strip())
    return json.loads(text.strip())


async def _call_llm(prompt: str, max_tokens: int = 4096) -> str:
    """Anthropic Claude API를 호출한다."""
    client = _get_client()
    response = await client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=max_tokens,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text


def _format_entry(entry: RightEntry) -> str:
    """RightEntry를 사람이 읽을 수 있는 문자열로 변환한다."""
    amount_str = f" {entry.amount:,}원" if entry.amount else ""
    date_str = entry.registration_date or "날짜미상"
    return f"[순위{entry.order}] {entry.right_type} | {entry.holder} | {date_str}{amount_str}"


# ---------------------------------------------------------------------------
# 1. 말소기준권리 판단
# ---------------------------------------------------------------------------


def determine_extinguishment_basis(
    section_a_entries: list[RightEntry],
    section_b_entries: list[RightEntry],
) -> tuple[str, str | None]:
    """말소기준권리를 판단한다.

    갑구+을구의 모든 권리 중 말소기준권리 대상 유형만 필터링하여,
    가장 먼저 설정된 권리를 말소기준권리로 결정한다.

    Returns:
        (설명 문자열, basis_date) — 해당 없으면 ("말소기준권리 없음", None)
    """
    all_entries = section_a_entries + section_b_entries
    eligible = [
        e
        for e in all_entries
        if e.right_type in EXTINGUISHMENT_ELIGIBLE_TYPES and e.registration_date
    ]

    if not eligible:
        return "말소기준권리 없음", None

    eligible.sort(key=lambda e: e.registration_date)  # type: ignore[arg-type]
    basis = eligible[0]
    desc = f"{basis.right_type} (순위{basis.order}, {basis.registration_date}, {basis.holder})"
    return desc, basis.registration_date


# ---------------------------------------------------------------------------
# 2. 권리 인수/소멸 판별
# ---------------------------------------------------------------------------


def classify_rights(
    all_entries: list[RightEntry],
    basis_date: str,
) -> tuple[list[str], list[str], int]:
    """말소기준권리 설정일을 기준으로 각 권리의 인수/소멸을 판별한다.

    Returns:
        (assumed 문자열 리스트, extinguished 문자열 리스트, 인수 총액)
    """
    assumed: list[str] = []
    extinguished: list[str] = []
    total_assumed_amount = 0

    for entry in all_entries:
        desc = _format_entry(entry)

        # 날짜가 없는 권리는 소멸로 처리
        if not entry.registration_date:
            extinguished.append(desc)
            continue

        if entry.registration_date < basis_date:
            # 선순위: 소유권이전 등 일반 소유권 관련은 제외하고 인수 판정
            if entry.right_type in ("소유권이전", "소유권보존"):
                continue
            assumed.append(desc)
            total_assumed_amount += entry.amount or 0
        else:
            extinguished.append(desc)

    return assumed, extinguished, total_assumed_amount


# ---------------------------------------------------------------------------
# 3. 임차인 분석
# ---------------------------------------------------------------------------


def analyze_tenants(
    occupancy_info: list[OccupancyInfo],
    basis_date: str,
) -> list[TenantAnalysis]:
    """임차인별 대항력·우선변제권을 분석한다."""
    results: list[TenantAnalysis] = []

    for occ in occupancy_info:
        # 소유자는 임차인 분석 대상이 아님
        if occ.occupant_type == "소유자":
            continue

        deposit = occ.deposit or 0

        # 대항력 판단: 전입일이 말소기준권리보다 선순위
        has_opposition = bool(
            occ.move_in_date and occ.move_in_date < basis_date
        )

        # 우선변제권: 대항력 + 소액임차인 기준 이하 보증금
        has_priority = has_opposition and deposit <= SMALL_DEPOSIT_THRESHOLD

        results.append(
            TenantAnalysis(
                name=occ.occupant_name,
                deposit=deposit,
                has_opposition_right=has_opposition,
                has_priority_repayment=has_priority,
                expected_dividend=None,
            )
        )

    return results


# ---------------------------------------------------------------------------
# 4. Claude 종합 분석
# ---------------------------------------------------------------------------


async def analyze_with_claude(
    section_a_entries: list[RightEntry],
    section_b_entries: list[RightEntry],
    occupancy_info: list[OccupancyInfo],
    basis_description: str,
    assumed_rights: list[str],
) -> dict:
    """Claude를 이용하여 특수 권리 해석 및 종합 위험도를 평가한다."""
    section_a_text = "\n".join(_format_entry(e) for e in section_a_entries) or "없음"
    section_b_text = "\n".join(_format_entry(e) for e in section_b_entries) or "없음"
    occupancy_text = "\n".join(
        f"{o.occupant_name} ({o.occupant_type}) | 보증금 {o.deposit or 0:,}원 | 전입일 {o.move_in_date or '미상'}"
        for o in occupancy_info
    ) or "없음"
    assumed_text = "\n".join(assumed_rights) or "없음"

    prompt = RIGHTS_ANALYSIS_PROMPT.format(
        basis_description=basis_description,
        section_a=section_a_text,
        section_b=section_b_text,
        occupancy=occupancy_text,
        assumed_rights=assumed_text,
    )

    raw = await _call_llm(prompt)
    data = _parse_json_response(raw)

    return {
        "risk_level": data.get("risk_level", "medium"),
        "risk_factors": data.get("risk_factors", []),
        "confidence": float(data.get("confidence", 0.5)),
        "warnings": data.get("warnings", []),
    }


# ---------------------------------------------------------------------------
# 5. 에이전트 노드
# ---------------------------------------------------------------------------


async def rights_analysis_node(state: AgentState) -> AgentState:
    """권리분석 에이전트 노드.

    처리 흐름:
    1. state에서 등기부등본 + 매각물건명세서 파싱 결과 가져오기
    2. 말소기준권리 판단
    3. 각 권리 인수/소멸 분류
    4. 임차인 분석
    5. Claude로 특수 권리 해석 + 위험도 종합 평가
    6. RightsAnalysisResult 생성하여 state에 저장
    """
    errors: list[str] = list(state.errors)
    registry = state.registry
    sale_item = state.sale_item

    if not registry:
        errors.append("권리분석 실패: 등기부등본 파싱 결과 없음")
        state.rights_analysis = None
        state.errors = errors
        return state

    try:
        # 1) 말소기준권리 판단
        basis_desc, basis_date = determine_extinguishment_basis(
            registry.section_a_entries,
            registry.section_b_entries,
        )
        logger.info("말소기준권리: %s", basis_desc)

        if basis_date is None:
            # 말소기준권리를 찾을 수 없는 경우 최소한의 결과 반환
            state.rights_analysis = RightsAnalysisResult(
                extinguishment_basis=basis_desc,
                risk_level=RiskLevel.HIGH,
                risk_factors=["말소기준권리를 특정할 수 없어 위험도가 높습니다"],
                confidence_score=0.3,
            )
            state.errors = errors
            return state

        # 2) 권리 인수/소멸 분류
        all_entries = registry.section_a_entries + registry.section_b_entries
        assumed, extinguished, total_assumed = classify_rights(all_entries, basis_date)

        # 3) 임차인 분석
        tenants: list[TenantAnalysis] = []
        if sale_item and sale_item.occupancy_info:
            tenants = analyze_tenants(sale_item.occupancy_info, basis_date)

        # 4) Claude 종합 분석
        occupancy = sale_item.occupancy_info if sale_item else []
        claude_result = await analyze_with_claude(
            registry.section_a_entries,
            registry.section_b_entries,
            occupancy,
            basis_desc,
            assumed,
        )

        risk_level_str = claude_result["risk_level"]
        try:
            risk_level = RiskLevel(risk_level_str)
        except ValueError:
            risk_level = RiskLevel.MEDIUM

        risk_factors = claude_result["risk_factors"]
        if claude_result["warnings"]:
            risk_factors.extend(claude_result["warnings"])

        # 5) 결과 조립
        result = RightsAnalysisResult(
            extinguishment_basis=basis_desc,
            assumed_rights=assumed,
            extinguished_rights=extinguished,
            tenants=tenants,
            risk_level=risk_level,
            risk_factors=risk_factors,
            total_assumed_amount=total_assumed,
            confidence_score=claude_result["confidence"],
        )

        state.rights_analysis = result

    except Exception as exc:
        logger.exception("권리분석 오류")
        errors.append(f"권리분석 오류: {exc}")
        state.rights_analysis = None

    state.errors = errors
    return state
