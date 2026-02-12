# Task-00: 인프라 보완 (파일 업로드 + WebSocket)

> **참조 스펙**: PRD-07 섹션 5.1, 5.2 (FR-07-001~007)
> **예상 작업 시간**: 3~4시간
> **선행 작업**: 없음 (모든 모듈의 기반)

---

## 목차

1. [파일 업로드 완성](#1-파일-업로드-완성)
2. [WebSocket 실시간 상태 전송](#2-websocket-실시간-상태-전송)
3. [분석 작업 비동기 실행 연동](#3-분석-작업-비동기-실행-연동)
4. [테스트 가이드](#4-테스트-가이드)

---

## 1. 파일 업로드 완성

### 1.1 파일 저장 로직 구현

> 참조 파일: `backend/app/api/v1/files.py`

현재 상태: 엔드포인트는 존재하지만 실제 디스크 저장 로직이 없음.

#### 구현 내용

```python
# backend/app/api/v1/files.py

import shutil
from pathlib import Path
from uuid import uuid4

from app.config import settings

async def upload_file(
    file: UploadFile,
    analysis_id: str,
    db: AsyncSession,
) -> UploadedFile:
    """
    1. uploads/{analysis_id}/ 디렉토리 생성
    2. 파일을 고유 이름으로 저장 (UUID + 원본 확장자)
    3. DB에 UploadedFile 레코드 생성
    """
    upload_dir = Path(settings.UPLOAD_DIR) / analysis_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_id = str(uuid4())
    stored_name = f"{file_id}.pdf"
    stored_path = upload_dir / stored_name

    with open(stored_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    file_size = stored_path.stat().st_size
    # DB 저장 ...
```

### 1.2 파일 크기 검증

```python
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
MAX_TOTAL_SIZE = 200 * 1024 * 1024  # 200MB

# 단일 파일 크기 검증
if file.size and file.size > MAX_FILE_SIZE:
    raise HTTPException(status_code=413, detail="파일 크기가 50MB를 초과합니다")

# MIME 타입 검증
if file.content_type != "application/pdf":
    raise HTTPException(status_code=400, detail="PDF 파일만 업로드 가능합니다")
```

### 1.3 파일 삭제 시 디스크 파일도 삭제

```python
# DELETE /files/{file_id} 에서 DB 삭제 + 디스크 파일 삭제
stored_path = Path(uploaded_file.stored_path)
if stored_path.exists():
    stored_path.unlink()
```

---

## 2. WebSocket 실시간 상태 전송

### 2.1 ConnectionManager 구현

> 참조 파일: `backend/app/api/websocket/` (신규 또는 기존 파일 확장)

```python
# backend/app/api/websocket/manager.py

from fastapi import WebSocket

class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: dict[str, list[WebSocket]] = {}

    async def connect(self, analysis_id: str, websocket: WebSocket) -> None:
        await websocket.accept()
        if analysis_id not in self.active_connections:
            self.active_connections[analysis_id] = []
        self.active_connections[analysis_id].append(websocket)

    def disconnect(self, analysis_id: str, websocket: WebSocket) -> None:
        if analysis_id in self.active_connections:
            self.active_connections[analysis_id].remove(websocket)

    async def send_progress(self, analysis_id: str, data: dict) -> None:
        if analysis_id in self.active_connections:
            for ws in self.active_connections[analysis_id]:
                await ws.send_json(data)

manager = ConnectionManager()
```

### 2.2 WebSocket 엔드포인트

```python
# backend/app/api/v1/websocket.py

@router.websocket("/ws/analyses/{analysis_id}")
async def analysis_progress(websocket: WebSocket, analysis_id: str):
    await manager.connect(analysis_id, websocket)
    try:
        while True:
            await websocket.receive_text()  # keep-alive
    except WebSocketDisconnect:
        manager.disconnect(analysis_id, websocket)
```

### 2.3 진행 상태 메시지 포맷

```python
# 에이전트 노드에서 호출
await manager.send_progress(analysis_id, {
    "type": "status_update",
    "stage": "rights_analysis",
    "status": "running",
    "progress": 60,
    "message": "권리분석을 수행하고 있습니다...",
})
```

---

## 3. 분석 작업 비동기 실행 연동

### 3.1 BackgroundTasks 연동

> 참조 파일: `backend/app/api/v1/analyses.py`

```python
from fastapi import BackgroundTasks

@router.post("", status_code=201)
async def create_analysis(
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    ...
):
    # 1. Analysis 레코드 생성 (status=pending)
    # 2. BackgroundTask로 분석 워크플로우 실행
    background_tasks.add_task(run_analysis_workflow, analysis.id)
    return analysis
```

### 3.2 분석 상태 조회 API 보완

```python
# GET /analyses/{id}/status
@router.get("/{analysis_id}/status")
async def get_analysis_status(analysis_id: str, db: AsyncSession = Depends(get_db)):
    analysis = await db.get(Analysis, analysis_id)
    if not analysis:
        raise HTTPException(status_code=404)

    return {
        "id": analysis.id,
        "status": analysis.status,
        "progress": build_progress(analysis),  # JSON 필드에서 진행률 계산
        "started_at": analysis.started_at,
    }
```

### 3.3 리포트 조회 API 보완

```python
# GET /analyses/{id}/report
@router.get("/{analysis_id}/report")
async def get_analysis_report(analysis_id: str, db: AsyncSession = Depends(get_db)):
    analysis = await db.get(Analysis, analysis_id)
    if not analysis:
        raise HTTPException(status_code=404)
    if analysis.status != "done":
        raise HTTPException(status_code=400, detail="분석이 아직 완료되지 않았습니다")

    return analysis.report
```

---

## 4. 테스트 가이드

### 4.1 테스트 케이스

| ID | 테스트명 | 설명 | 기대 결과 |
|:---:|:---|:---|:---|
| T-1 | `test_upload_pdf_success` | 정상 PDF 업로드 | 201, 파일 DB 저장 + 디스크 저장 |
| T-2 | `test_upload_non_pdf_rejected` | txt 파일 업로드 | 400, 에러 메시지 |
| T-3 | `test_upload_oversize_rejected` | 50MB 초과 파일 | 413, 에러 메시지 |
| T-4 | `test_delete_file_removes_disk` | 파일 삭제 | DB + 디스크 모두 삭제 |
| T-5 | `test_websocket_connect` | WebSocket 연결 | 연결 성공 |
| T-6 | `test_create_analysis_returns_pending` | 분석 생성 | 201, status=pending |
| T-7 | `test_get_report_before_done` | 미완료 분석 리포트 조회 | 400 |

### 4.2 테스트 실행

```bash
cd backend
uv run pytest tests/ -v
```

---

## 파일 변경 요약

### 수정 파일

| 파일 경로 | 변경 내용 |
|:---|:---|
| `backend/app/api/v1/files.py` | 디스크 저장, 크기 검증, 삭제 로직 추가 |
| `backend/app/api/v1/analyses.py` | BackgroundTasks 연동, status/report API 보완 |

### 신규 생성 파일

| 파일 경로 | 설명 |
|:---|:---|
| `backend/app/api/websocket/manager.py` | WebSocket ConnectionManager |
