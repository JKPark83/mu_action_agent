# PRD-07: 백엔드 API (Backend API)

> **문서 버전**: v1.0
> **작성일**: 2026-02-12
> **상태**: Draft
> **상위 문서**: PRD-00 시스템 개요

---

## 1. 개요

### 1.1 목적
FastAPI 기반의 백엔드 서버를 구축하여 프론트엔드와 AI 에이전트 시스템 간의 통신을 관리하고, 파일 업로드, 분석 작업 관리, 결과 조회 등의 기능을 제공한다.

### 1.2 기술 스택
| 항목 | 기술 | 비고 |
|------|------|------|
| **프레임워크** | FastAPI | Python 3.11+ |
| **ASGI 서버** | Uvicorn | 비동기 서버 |
| **패키지 관리** | uv | 빠른 패키지 관리 및 가상환경 |
| **데이터베이스** | SQLite (개발) / PostgreSQL (프로덕션) | SQLAlchemy ORM |
| **작업 큐** | 내장 BackgroundTasks / Celery (확장 시) | 비동기 분석 작업 |
| **파일 저장** | 로컬 파일시스템 | 업로드된 PDF 저장 |
| **API 문서** | Swagger UI (자동 생성) | /docs 엔드포인트 |

---

## 2. API 엔드포인트 설계

### 2.1 분석 관련 API

| Method | Endpoint | 설명 |
|--------|----------|------|
| `POST` | `/api/v1/analyses` | 새 분석 작업 생성 (PDF 업로드 포함) |
| `GET` | `/api/v1/analyses` | 분석 작업 목록 조회 |
| `GET` | `/api/v1/analyses/{id}` | 특정 분석 작업 상세 조회 |
| `GET` | `/api/v1/analyses/{id}/status` | 분석 진행 상태 조회 |
| `GET` | `/api/v1/analyses/{id}/report` | 분석 결과 리포트 조회 |
| `DELETE` | `/api/v1/analyses/{id}` | 분석 작업 삭제 |

### 2.2 파일 관련 API

| Method | Endpoint | 설명 |
|--------|----------|------|
| `POST` | `/api/v1/files/upload` | PDF 파일 업로드 |
| `GET` | `/api/v1/files/{id}` | 업로드된 파일 정보 조회 |
| `DELETE` | `/api/v1/files/{id}` | 파일 삭제 |

### 2.3 실시간 상태 API

| Method | Endpoint | 설명 |
|--------|----------|------|
| `WS` | `/api/v1/ws/analyses/{id}` | 분석 진행 상태 WebSocket |

### 2.4 시스템 API

| Method | Endpoint | 설명 |
|--------|----------|------|
| `GET` | `/api/v1/health` | 서버 상태 확인 |
| `GET` | `/docs` | Swagger UI API 문서 |

---

## 3. API 상세 명세

### 3.1 분석 작업 생성
```
POST /api/v1/analyses
Content-Type: multipart/form-data

Request:
  files: File[] (PDF 파일들)
  metadata: {
    "description": "서울시 강남구 역삼동 아파트 경매 분석",  // 선택
    "case_number": "2025타경12345"                          // 선택
  }

Response: 201 Created
{
  "id": "uuid",
  "status": "pending",
  "created_at": "2026-02-12T10:00:00Z",
  "files": [
    {
      "id": "uuid",
      "filename": "등기부등본.pdf",
      "document_type": null,
      "size": 1024000
    }
  ]
}
```

### 3.2 분석 상태 조회
```
GET /api/v1/analyses/{id}/status

Response: 200 OK
{
  "id": "uuid",
  "status": "running",
  "progress": {
    "overall": 45,
    "stages": {
      "document_parsing": { "status": "done", "progress": 100 },
      "rights_analysis": { "status": "running", "progress": 60 },
      "market_data": { "status": "running", "progress": 30 },
      "news_analysis": { "status": "running", "progress": 20 },
      "valuation": { "status": "pending", "progress": 0 },
      "report_generation": { "status": "pending", "progress": 0 }
    }
  },
  "started_at": "2026-02-12T10:00:05Z",
  "estimated_completion": "2026-02-12T10:03:00Z"
}
```

### 3.3 분석 결과 리포트 조회
```
GET /api/v1/analyses/{id}/report

Response: 200 OK
{
  "id": "uuid",
  "case_number": "2025타경12345",
  "property_address": "서울시 강남구 역삼동 123-45",
  "recommendation": "추천",
  "recommendation_reason": "...",
  "bid_price": {
    "conservative": 350000000,
    "moderate": 380000000,
    "aggressive": 420000000,
    "minimum_bid": 320000000
  },
  "sale_price": {
    "pessimistic": 450000000,
    "base": 480000000,
    "optimistic": 520000000
  },
  "profitability": { ... },
  "cost_breakdown": { ... },
  "risk_assessment": { ... },
  "rights_analysis_summary": "...",
  "market_summary": "...",
  "news_summary": "...",
  "overall_opinion": "...",
  "confidence_score": 0.85,
  "disclaimer": "본 분석 결과는 AI에 의한 참고용 정보이며...",
  "created_at": "2026-02-12T10:03:00Z"
}
```

### 3.4 WebSocket 진행 상태
```
WS /api/v1/ws/analyses/{id}

Server → Client Messages:
{
  "type": "status_update",
  "stage": "rights_analysis",
  "status": "done",
  "progress": 100,
  "message": "권리분석이 완료되었습니다."
}

{
  "type": "analysis_complete",
  "report_url": "/api/v1/analyses/{id}/report"
}

{
  "type": "error",
  "stage": "market_data",
  "message": "실거래가 API 호출에 실패했습니다. 재시도 중..."
}
```

---

## 4. 데이터 모델 (DB)

### 4.1 분석 작업 (Analysis)
```python
class Analysis(Base):
    __tablename__ = "analyses"

    id: str                             # UUID
    status: str                         # pending | running | done | error
    description: str | None             # 사용자 메모
    case_number: str | None             # 사건번호

    # 분석 결과 (JSON)
    parsed_documents: dict | None
    rights_analysis: dict | None
    market_data: dict | None
    news_analysis: dict | None
    valuation: dict | None
    report: dict | None

    # 에러 정보
    errors: list[str] | None

    # 타임스탬프
    created_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
```

### 4.2 업로드 파일 (UploadedFile)
```python
class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id: str                             # UUID
    analysis_id: str                    # FK → Analysis
    filename: str                       # 원본 파일명
    stored_path: str                    # 저장 경로
    file_size: int                      # 파일 크기 (bytes)
    document_type: str | None           # 문서 유형 (자동 분류 후)
    created_at: datetime
```

---

## 5. 기능 요구사항

### 5.1 파일 관리
- **FR-07-001**: PDF 파일을 멀티파트 형태로 업로드할 수 있어야 한다
- **FR-07-002**: 업로드 파일 크기를 제한해야 한다 (단일 50MB, 전체 200MB)
- **FR-07-003**: PDF 파일만 허용해야 한다 (MIME 타입 검증)
- **FR-07-004**: 업로드된 파일은 고유한 경로에 안전하게 저장해야 한다

### 5.2 분석 작업 관리
- **FR-07-005**: 분석 작업을 비동기로 실행해야 한다 (업로드 즉시 응답 반환)
- **FR-07-006**: 분석 진행 상태를 실시간으로 조회할 수 있어야 한다
- **FR-07-007**: WebSocket을 통한 실시간 상태 업데이트를 지원해야 한다
- **FR-07-008**: 분석 작업의 이력을 조회할 수 있어야 한다

### 5.3 결과 관리
- **FR-07-009**: 분석 결과를 구조화된 JSON으로 반환해야 한다
- **FR-07-010**: 분석 결과를 DB에 영구 저장해야 한다
- **FR-07-011**: 분석 작업과 관련 파일을 삭제할 수 있어야 한다

### 5.4 에러 처리
- **FR-07-012**: API 에러 응답을 일관된 형식으로 반환해야 한다
- **FR-07-013**: 입력값 검증 실패 시 명확한 에러 메시지를 제공해야 한다
- **FR-07-014**: 예외 발생 시 적절한 HTTP 상태 코드를 반환해야 한다

---

## 6. 프로젝트 구조

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py                     # FastAPI 앱 생성 및 라우터 등록
│   ├── config.py                   # 환경 설정 (Settings)
│   ├── api/
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── router.py           # v1 라우터 통합
│   │   │   ├── analyses.py         # 분석 API 엔드포인트
│   │   │   ├── files.py            # 파일 API 엔드포인트
│   │   │   └── websocket.py        # WebSocket 엔드포인트
│   │   └── deps.py                 # 의존성 주입
│   ├── models/
│   │   ├── __init__.py
│   │   ├── analysis.py             # Analysis 모델
│   │   └── file.py                 # UploadedFile 모델
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── analysis.py             # 분석 관련 Pydantic 스키마
│   │   └── file.py                 # 파일 관련 Pydantic 스키마
│   ├── services/
│   │   ├── __init__.py
│   │   ├── analysis_service.py     # 분석 비즈니스 로직
│   │   └── file_service.py         # 파일 관리 비즈니스 로직
│   └── db/
│       ├── __init__.py
│       ├── database.py             # DB 연결 설정
│       └── session.py              # 세션 관리
├── pyproject.toml                  # 프로젝트 메타데이터 및 의존성
├── .python-version                 # Python 버전 (3.11+)
└── .env.example                    # 환경변수 예시
```

---

## 7. 환경 설정

### 7.1 환경변수
```env
# Server
APP_HOST=0.0.0.0
APP_PORT=8000
APP_ENV=development

# Database
DATABASE_URL=sqlite:///./data/auction.db

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...

# 국토교통부 API
MOLIT_API_KEY=...

# 뉴스 API
NEWS_API_KEY=...

# File Storage
UPLOAD_DIR=./uploads
MAX_FILE_SIZE=52428800  # 50MB
```

---

## 8. 비기능 요구사항

- **응답 시간**: API 응답 500ms 이내 (분석 작업 생성/조회)
- **동시 접속**: 최소 10명 동시 사용자 지원
- **API 문서**: Swagger UI 자동 생성
- **CORS**: 프론트엔드 도메인 허용
- **로깅**: 모든 API 요청/응답 로깅
- **에러 응답 형식**: `{"detail": "message", "status_code": 400}` 통일

---

## 9. 추후 상세화 필요 사항
- [ ] 인증/인가 시스템 (필요 시 추가)
- [ ] API rate limiting 전략
- [ ] DB 마이그레이션 전략 (Alembic)
- [ ] 파일 저장소 확장 (S3 등 클라우드 스토리지)
- [ ] 배포 전략 (Docker, docker-compose)
- [ ] CI/CD 파이프라인
- [ ] API 버저닝 전략 상세화
- [ ] 모니터링 및 관측성 (로그 수집, 메트릭)

---

## 변경 이력

| 버전 | 날짜 | 변경 내용 |
|------|------|----------|
| v1.0 | 2026-02-12 | 초안 작성 |
| v1.1 | 2026-02-13 | SQLAlchemy SQL 로그 기본 비활성화 (echo=False). 분석 파이프라인 진행 상황을 파악할 수 있는 구조화된 로깅 추가 (로깅 포맷 통일, 색상 구분) |
