from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class FileResponse:
    id: str
    analysis_id: str
    filename: str
    file_size: int
    document_type: str | None
    created_at: datetime
