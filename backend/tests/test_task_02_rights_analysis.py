"""Task-02: 권리분석 에이전트 단위 테스트

LLM 호출은 모두 mock 처리하여 외부 의존성 없이 테스트한다.
"""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.agents.nodes.rights_analysis import (
    analyze_tenants,
    classify_rights,
    determine_extinguishment_basis,
    rights_analysis_node,
)
from app.agents.state import AgentState
from app.schemas.document import OccupancyInfo, RegistryExtraction, RightEntry


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mortgage_entry() -> RightEntry:
    """근저당권 (을구, 2020-02-01)"""
    return RightEntry(
        order=1,
        right_type="근저당권설정",
        holder="주식회사 좋은은행",
        amount=200_000_000,
        registration_date="2020-02-01",
    )


@pytest.fixture
def seizure_entry() -> RightEntry:
    """가압류 (갑구, 2023-05-10)"""
    return RightEntry(
        order=2,
        right_type="가압류",
        holder="주식회사 좋은은행",
        amount=50_000_000,
        registration_date="2023-05-10",
    )


@pytest.fixture
def jeonse_entry() -> RightEntry:
    """선순위 전세권 (을구, 2019-06-15)"""
    return RightEntry(
        order=1,
        right_type="전세권설정",
        holder="김철수",
        amount=150_000_000,
        registration_date="2019-06-15",
    )


@pytest.fixture
def post_mortgage_entry() -> RightEntry:
    """후순위 근저당 (을구, 2022-03-20)"""
    return RightEntry(
        order=2,
        right_type="근저당권설정",
        holder="주식회사 나쁜은행",
        amount=100_000_000,
        registration_date="2022-03-20",
    )


# ---------------------------------------------------------------------------
# T-1: 말소기준권리 판단 (기본)
# ---------------------------------------------------------------------------


def test_extinguishment_basis_basic(mortgage_entry: RightEntry):
    """근저당 1건만 있으면 해당 근저당이 말소기준권리가 된다."""
    desc, basis_date = determine_extinguishment_basis(
        section_a_entries=[],
        section_b_entries=[mortgage_entry],
    )

    assert basis_date == "2020-02-01"
    assert "근저당권설정" in desc
    assert "좋은은행" in desc


# ---------------------------------------------------------------------------
# T-2: 말소기준권리 판단 (복수 권리)
# ---------------------------------------------------------------------------


def test_extinguishment_basis_multiple(
    mortgage_entry: RightEntry, seizure_entry: RightEntry
):
    """근저당(2020-02-01) + 가압류(2023-05-10) → 먼저 설정된 근저당이 기준."""
    desc, basis_date = determine_extinguishment_basis(
        section_a_entries=[seizure_entry],
        section_b_entries=[mortgage_entry],
    )

    assert basis_date == "2020-02-01"
    assert "근저당권설정" in desc


# ---------------------------------------------------------------------------
# T-3: 선순위 전세권 → 인수
# ---------------------------------------------------------------------------


def test_classify_prior_right_assumed(
    jeonse_entry: RightEntry, mortgage_entry: RightEntry
):
    """말소기준(2020-02-01)보다 선순위 전세권(2019-06-15)은 인수 판정."""
    basis_date = "2020-02-01"
    assumed, extinguished, total = classify_rights(
        [jeonse_entry, mortgage_entry], basis_date
    )

    assert len(assumed) == 1
    assert "전세권설정" in assumed[0]
    assert total == 150_000_000


# ---------------------------------------------------------------------------
# T-4: 후순위 근저당 → 소멸
# ---------------------------------------------------------------------------


def test_classify_post_right_extinguished(
    mortgage_entry: RightEntry, post_mortgage_entry: RightEntry
):
    """말소기준(2020-02-01) 이후 근저당(2022-03-20)은 소멸 판정."""
    basis_date = "2020-02-01"
    assumed, extinguished, total = classify_rights(
        [mortgage_entry, post_mortgage_entry], basis_date
    )

    # mortgage_entry 자체는 basis_date와 같으므로 소멸
    # post_mortgage_entry는 후순위이므로 소멸
    extinguished_text = " ".join(extinguished)
    assert "나쁜은행" in extinguished_text
    assert total == 0


# ---------------------------------------------------------------------------
# T-5: 대항력 있는 임차인
# ---------------------------------------------------------------------------


def test_tenant_with_opposition():
    """전입일(2019-01-01)이 말소기준(2020-02-01)보다 선순위 → 대항력 있음."""
    occ = OccupancyInfo(
        occupant_name="김철수",
        occupant_type="임차인",
        deposit=100_000_000,
        monthly_rent=0,
        move_in_date="2019-01-01",
    )

    tenants = analyze_tenants([occ], "2020-02-01")

    assert len(tenants) == 1
    assert tenants[0].has_opposition_right is True
    assert tenants[0].deposit == 100_000_000


# ---------------------------------------------------------------------------
# T-6: 대항력 없는 임차인
# ---------------------------------------------------------------------------


def test_tenant_without_opposition():
    """전입일(2021-06-01)이 말소기준(2020-02-01)보다 후순위 → 대항력 없음."""
    occ = OccupancyInfo(
        occupant_name="이영희",
        occupant_type="임차인",
        deposit=50_000_000,
        monthly_rent=500_000,
        move_in_date="2021-06-01",
    )

    tenants = analyze_tenants([occ], "2020-02-01")

    assert len(tenants) == 1
    assert tenants[0].has_opposition_right is False


# ---------------------------------------------------------------------------
# T-7: 등기부 없는 경우 에러 처리
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rights_analysis_node_no_registry():
    """등기부등본 파싱 결과가 없으면 에러 메시지를 추가한다."""
    state = AgentState(analysis_id="test-no-reg")
    # registry가 None인 상태

    result = await rights_analysis_node(state)

    assert result.rights_analysis is None
    assert len(result.errors) == 1
    assert "등기부등본" in result.errors[0]
