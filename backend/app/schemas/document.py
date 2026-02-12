"""문서 파싱 결과 스키마 (등기부등본, 감정평가서, 매각물건명세서 등)"""

from dataclasses import dataclass, field
from enum import Enum


class DocumentType(str, Enum):
    REGISTRY = "registry"  # 등기부등본
    APPRAISAL = "appraisal"  # 감정평가서
    SALE_ITEM = "sale_item"  # 매각물건명세서
    STATUS_REPORT = "status_report"  # 현황조사보고서
    CASE_NOTICE = "case_notice"  # 사건송달내역


@dataclass(frozen=True)
class RightEntry:
    """등기부 권리 항목"""

    order: int
    right_type: str  # 근저당, 전세권, 가압류 등
    holder: str
    amount: int | None = None
    registration_date: str | None = None


@dataclass(frozen=True)
class RegistryExtraction:
    """등기부등본 추출 결과"""

    property_address: str
    property_type: str
    area: float | None = None
    owner: str | None = None
    section_a_entries: list[RightEntry] = field(default_factory=list)  # 갑구
    section_b_entries: list[RightEntry] = field(default_factory=list)  # 을구


@dataclass(frozen=True)
class OccupancyInfo:
    """점유자 정보"""

    occupant_name: str
    occupant_type: str  # 임차인, 소유자, 기타
    deposit: int | None = None
    monthly_rent: int | None = None
    move_in_date: str | None = None


@dataclass(frozen=True)
class AppraisalExtraction:
    """감정평가서 추출 결과"""

    appraised_value: int
    land_value: int | None = None
    building_value: int | None = None
    land_area: float | None = None
    building_area: float | None = None


@dataclass(frozen=True)
class SaleItemExtraction:
    """매각물건명세서 추출 결과"""

    case_number: str
    property_address: str
    occupancy_info: list[OccupancyInfo] = field(default_factory=list)
    assumed_rights: list[str] = field(default_factory=list)
    special_conditions: list[str] = field(default_factory=list)
