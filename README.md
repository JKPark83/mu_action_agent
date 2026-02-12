# 부동산 경매 분석 AI 시스템

한국 부동산 경매 문서를 AI로 분석하여 입찰 추천, 적정 입찰가, 예상 매각가, 투자 수익률을 제공하는 시스템입니다.

## 기술 스택

| 영역 | 기술 |
|------|------|
| Frontend | React 19, TypeScript, Vite, Tailwind CSS, TanStack Query |
| Backend | FastAPI, SQLAlchemy 2.0 (async), Alembic |
| AI | LangGraph, LangChain, Anthropic Claude API |
| 문서처리 | pdfplumber, pypdf2, pytesseract (OCR) |

## 사전 요구사항

- Python 3.11+
- Node.js 20.19+ 또는 22.12+ & npm (Vite 7 요구사항)
- [uv](https://docs.astral.sh/uv/) (Python 패키지 매니저)

## 환경 설정

```bash
cp .env.example .env
```

`.env` 파일을 열어 API 키를 입력합니다:

```
ANTHROPIC_API_KEY=sk-ant-xxxxx   # (필수) Claude AI 호출용
MOLIT_API_KEY=your-api-key       # (선택) 국토교통부 공공데이터 API
NAVER_CLIENT_ID=your-client-id   # (선택) 네이버 뉴스 API
NAVER_CLIENT_SECRET=your-secret  # (선택) 네이버 뉴스 API
```

## 실행 방법

### 1. 백엔드 (Port 8000)

```bash
cd backend
uv sync
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. 프론트엔드 (Port 5173)

```bash
cd frontend
npm install
npm run dev
```

> 백엔드를 먼저 실행한 뒤 프론트엔드를 실행하세요. Vite에 `/api` → `localhost:8000` 프록시가 설정되어 있습니다.

## 접속 URL

| 서비스 | URL |
|--------|-----|
| 프론트엔드 | http://localhost:5173 |
| API 문서 (Swagger) | http://localhost:8000/docs |
| API 문서 (ReDoc) | http://localhost:8000/redoc |

## 프로젝트 구조

```
my_auction/
├── frontend/          # React SPA
│   └── src/
│       ├── pages/     # Home, AnalysisProgress, Report, History
│       ├── components/
│       ├── hooks/     # useAnalysis, useFileUpload, useWebSocket
│       ├── api/       # Axios API 클라이언트
│       └── types/     # TypeScript 타입 정의
├── backend/           # FastAPI 서버
│   └── app/
│       ├── main.py    # 앱 진입점
│       ├── api/v1/    # REST API 엔드포인트
│       ├── agents/    # LangGraph AI 에이전트
│       ├── models/    # SQLAlchemy 모델
│       └── schemas/   # Pydantic 스키마
└── docs/              # PRD 문서
```

## 주요 API 엔드포인트

| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/api/v1/files/upload` | PDF 파일 업로드 |
| POST | `/api/v1/analyses` | 분석 작업 생성 |
| GET | `/api/v1/analyses` | 분석 목록 조회 |
| GET | `/api/v1/analyses/{id}` | 분석 상세 조회 |
| GET | `/api/v1/analyses/{id}/status` | 실시간 상태 조회 |
| GET | `/api/v1/analyses/{id}/report` | 분석 리포트 조회 |
