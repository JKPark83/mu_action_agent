from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class AnalysisStatusEnum(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


class StageStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


@dataclass(frozen=True)
class StageProgress:
    status: StageStatus = StageStatus.PENDING
    progress: int = 0


@dataclass(frozen=True)
class AnalysisProgress:
    overall: int = 0
    document_parsing: StageProgress = field(default_factory=StageProgress)
    rights_analysis: StageProgress = field(default_factory=StageProgress)
    market_data: StageProgress = field(default_factory=StageProgress)
    news_analysis: StageProgress = field(default_factory=StageProgress)
    valuation: StageProgress = field(default_factory=StageProgress)
    report_generation: StageProgress = field(default_factory=StageProgress)


@dataclass(frozen=True)
class AnalysisCreate:
    description: str | None = None
    case_number: str | None = None


@dataclass(frozen=True)
class AnalysisResponse:
    id: str
    status: AnalysisStatusEnum
    description: str | None
    case_number: str | None
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None


@dataclass(frozen=True)
class AnalysisDetail(AnalysisResponse):
    parsed_documents: dict | None = None
    rights_analysis: dict | None = None
    market_data: dict | None = None
    news_analysis: dict | None = None
    valuation: dict | None = None
    report: dict | None = None
    errors: dict | None = None
