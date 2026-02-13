import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AnalysisStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


class Analysis(Base):
    __tablename__ = "analyses"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    status: Mapped[AnalysisStatus] = mapped_column(Enum(AnalysisStatus), default=AnalysisStatus.PENDING)
    description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    case_number: Mapped[str | None] = mapped_column(String(100), nullable=True)

    # 분석 결과 (JSON)
    parsed_documents: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    rights_analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    market_data: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    news_analysis: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    valuation: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    report: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    errors: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # 대시보드 요약 필드
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=False, server_default="0")
    property_address: Mapped[str | None] = mapped_column(String(500), nullable=True)
    property_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    property_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    area: Mapped[float | None] = mapped_column(Float, nullable=True)
    appraised_value: Mapped[int | None] = mapped_column(Integer, nullable=True)
    recommendation: Mapped[str | None] = mapped_column(String(20), nullable=True)
    expected_roi: Mapped[float | None] = mapped_column(Float, nullable=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # 타임스탬프
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # 관계
    files: Mapped[list["UploadedFile"]] = relationship("UploadedFile", back_populates="analysis", cascade="all, delete-orphan")  # noqa: F821
