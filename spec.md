# AuctionAI - 부동산 경매 분석 시스템 스펙 문서

> 본 문서는 현재 구현된 모든 기능에 대한 상세 명세입니다.
> 추후 기능 변경 및 업그레이드 시 기준 문서로 활용됩니다.
> 최종 업데이트: 2026-02-13

---

## 목차

- [1. BE 구현사항](#1-be-구현사항)
  - [1.1 기술 스택](#11-기술-스택)
  - [1.2 프로젝트 구조](#12-프로젝트-구조)
  - [1.3 API 엔드포인트](#13-api-엔드포인트)
  - [1.4 데이터 모델](#14-데이터-모델)
  - [1.5 AI 에이전트 파이프라인](#15-ai-에이전트-파이프라인)
  - [1.6 외부 API 연동](#16-외부-api-연동)
  - [1.7 WebSocket 실시간 통신](#17-websocket-실시간-통신)
  - [1.8 에러 처리 및 재시도](#18-에러-처리-및-재시도)
- [2. 리포트 생성 요구사항](#2-리포트-생성-요구사항)
  - [2.1 투자 추천 생성 기준](#21-투자-추천-생성-기준)
  - [2.2 가격 분석 기준](#22-가격-분석-기준)
  - [2.3 시세 추이 분석](#23-시세-추이-분석)
  - [2.4 권리분석 상세 기준](#24-권리분석-상세-기준)
  - [2.5 뉴스/시장동향 분석](#25-뉴스시장동향-분석)
  - [2.6 최종 리포트 구조](#26-최종-리포트-구조)
- [3. FE 구현사항](#3-fe-구현사항)
  - [3.1 기술 스택](#31-기술-스택)
  - [3.2 페이지 구성](#32-페이지-구성)
  - [3.3 컴포넌트 구조](#33-컴포넌트-구조)
  - [3.4 상태 관리 및 데이터 흐름](#34-상태-관리-및-데이터-흐름)
  - [3.5 타입 시스템](#35-타입-시스템)
- [4. 테스트 현황](#4-테스트-현황)

---

# 1. BE 구현사항

## 1.1 기술 스택

| 항목 | 기술 | 버전/비고 |
|------|------|-----------|
| 프레임워크 | FastAPI | 비동기 Python 웹 프레임워크 |
| 데이터베이스 | SQLite + aiosqlite | 비동기 SQLite (기본: `auction.db`) |
| ORM | SQLAlchemy | 비동기 세션 (`AsyncSession`) |
| AI 엔진 | Anthropic Claude Sonnet 4.5 | `claude-sonnet-4-5-20250929` |
| 워크플로우 | LangGraph 패턴 (커스텀) | 순차+병렬 노드 실행 |
| PDF 파싱 | pdfplumber + pytesseract(OCR 폴백) | |
| 설정 관리 | pydantic-settings | `.env` 파일 기반 |
| HTTP 클라이언트 | httpx | 비동기 외부 API 호출 |

### 환경 변수 (`.env`)

| 변수명 | 설명 | 기본값 |
|--------|------|--------|
| `APP_ENV` | 실행 환경 | `development` |
| `DEBUG` | 디버그 모드 | `True` |
| `DATABASE_URL` | DB 연결 문자열 | `sqlite+aiosqlite:///./auction.db` |
| `ANTHROPIC_API_KEY` | Claude API 키 | (필수) |
| `MOLIT_API_KEY` | 국토교통부 실거래가 API 키 | (필수) |
| `NAVER_CLIENT_ID` | 네이버 뉴스 검색 API Client ID | (필수) |
| `NAVER_CLIENT_SECRET` | 네이버 뉴스 검색 API Client Secret | (필수) |
| `UPLOAD_DIR` | 파일 업로드 디렉토리 | `./uploads` |
| `MAX_FILE_SIZE_MB` | 최대 단일 파일 크기 | `50` (MB) |
| `MAX_TOTAL_SIZE_MB` | 최대 총 파일 크기 | `200` (MB) |
| `HOST` | 서버 호스트 | `0.0.0.0` |
| `PORT` | 서버 포트 | `8000` |

## 1.2 프로젝트 구조

```
backend/
├── app/
│   ├── main.py                     # FastAPI 앱 초기화, CORS, 라우터 등록
│   ├── config.py                   # pydantic-settings 기반 환경 설정
│   ├── database.py                 # SQLAlchemy 비동기 엔진/세션 설정
│   ├── api/
│   │   ├── router.py               # API 라우터 통합 (/api/v1)
│   │   ├── deps.py                 # 의존성 (get_db 세션)
│   │   ├── v1/
│   │   │   ├── analyses.py         # 분석 CRUD + 워크플로우 트리거
│   │   │   ├── files.py            # 파일 업로드/조회/삭제
│   │   │   └── health.py           # 헬스체크
│   │   └── websocket/
│   │       ├── analyses.py         # WebSocket 엔드포인트
│   │       └── manager.py          # ConnectionManager (WS 관리)
│   ├── models/
│   │   ├── analysis.py             # Analysis 모델 (SQLAlchemy)
│   │   └── file.py                 # UploadedFile 모델
│   ├── schemas/
│   │   ├── analysis.py             # 분석 관련 스키마
│   │   ├── document.py             # 문서 파싱 결과 스키마
│   │   ├── market.py               # 시세 데이터 스키마
│   │   ├── news.py                 # 뉴스 분석 스키마
│   │   ├── rights.py               # 권리분석 스키마
│   │   └── valuation.py            # 가치평가 스키마
│   └── agents/
│       ├── graph.py                # 워크플로우 실행 엔진
│       ├── state.py                # AgentState 상태 정의
│       ├── nodes/
│       │   ├── document_parser.py  # 문서 파싱 노드
│       │   ├── rights_analysis.py  # 권리분석 노드
│       │   ├── market_data.py      # 시세분석 노드
│       │   ├── news_analysis.py    # 뉴스분석 노드
│       │   ├── valuation.py        # 가치평가 노드
│       │   └── report_generator.py # 보고서 생성 노드
│       ├── prompts/
│       │   ├── document_prompts.py # 문서 분류/추출 프롬프트
│       │   ├── rights_prompts.py   # 권리분석 프롬프트
│       │   ├── news_prompts.py     # 뉴스분석 프롬프트
│       │   └── report_prompts.py   # 리포트 생성 프롬프트
│       └── tools/
│           ├── pdf_extractor.py    # PDF 텍스트/테이블 추출
│           ├── address_converter.py# 주소 → 법정동코드 변환
│           ├── real_estate_api.py  # 국토교통부 실거래가 API
│           └── news_api.py         # 네이버 뉴스 검색 API
└── tests/                          # 단위 테스트
```

## 1.3 API 엔드포인트

### 분석(Analyses) API — `/api/v1/analyses`

| Method | Path | 설명 | 요청 | 응답 |
|--------|------|------|------|------|
| `POST` | `/api/v1/analyses` | 분석 생성 + 워크플로우 시작 | `multipart/form-data`: files(PDF[]), description?, case_number? | `{id, status}` (201) |
| `GET` | `/api/v1/analyses` | 분석 목록 조회 | - | `[{id, status, description, case_number, created_at}]` |
| `GET` | `/api/v1/analyses/{id}` | 분석 상세 조회 | - | `{id, status, description, case_number, created_at, started_at, completed_at, report, rights_analysis, market_data, news_analysis, valuation}` |
| `GET` | `/api/v1/analyses/{id}/status` | 분석 진행 상태 조회 | - | `{id, status, progress: {overall, stages}, started_at}` |
| `GET` | `/api/v1/analyses/{id}/report` | 완료된 리포트 조회 | - | report JSON (done 상태일 때만) |
| `DELETE` | `/api/v1/analyses/{id}` | 분석 삭제 | - | `{detail: "삭제되었습니다."}` |

### 파일(Files) API — `/api/v1/files`

| Method | Path | 설명 | 요청 | 응답 |
|--------|------|------|------|------|
| `POST` | `/api/v1/files/upload` | PDF 파일 업로드 | `analysis_id` + `file` (multipart) | `{id, filename}` (201) |
| `GET` | `/api/v1/files/{id}` | 파일 정보 조회 | - | `{id, filename, file_size, document_type}` |
| `DELETE` | `/api/v1/files/{id}` | 파일 삭제 (DB+디스크) | - | `{detail: "삭제되었습니다."}` |

### 기타

| Method | Path | 설명 |
|--------|------|------|
| `GET` | `/api/v1/health` | 헬스체크 → `{status: "ok"}` |
| `WebSocket` | `/ws/analyses/{id}` | 분석 진행 상태 실시간 스트리밍 |

### 파일 업로드 제약사항

- **허용 형식**: PDF만 (`.pdf` 확장자 + `application/pdf` MIME 타입)
- **최대 크기**: 50MB/파일
- **저장 방식**: `uploads/{analysis_id}/{uuid}.pdf` 형태로 UUID 기반 이름으로 저장

## 1.4 데이터 모델

### Analysis (분석 작업)

| 필드 | 타입 | 설명 |
|------|------|------|
| `id` | `String` (UUID) | PK, 자동 생성 |
| `status` | `Enum` | `pending` / `running` / `done` / `error` |
| `description` | `String?` | 분석 설명 |
| `case_number` | `String?` | 사건번호 |
| `created_at` | `DateTime` | 생성 시각 (UTC) |
| `started_at` | `DateTime?` | 분석 시작 시각 |
| `completed_at` | `DateTime?` | 분석 완료 시각 |
| `parsed_documents` | `JSON?` | 문서 파싱 결과 |
| `rights_analysis` | `JSON?` | 권리분석 결과 |
| `market_data` | `JSON?` | 시세분석 결과 |
| `news_analysis` | `JSON?` | 뉴스분석 결과 |
| `valuation` | `JSON?` | 가치평가 결과 |
| `report` | `JSON?` | 최종 리포트 |
| `errors` | `JSON?` | 에러 로그 |

### UploadedFile (업로드 파일)

| 필드 | 타입 | 설명 |
|------|------|------|
| `id` | `String` (UUID) | PK |
| `analysis_id` | `String` | FK → Analysis |
| `filename` | `String` | 원본 파일명 |
| `stored_path` | `String` | 디스크 저장 경로 |
| `file_size` | `Integer` | 파일 크기 (bytes) |
| `document_type` | `String?` | 문서 분류 결과 |

## 1.5 AI 에이전트 파이프라인

### 워크플로우 실행 순서

```
[PDF 파일 입력]
      │
      ▼
[1. document_parser]      ── 순차 실행
      │
      ├──────────────────────────────┐
      ▼                              ▼
[2a. rights_analysis]   [2b. market_data]   [2c. news_analysis]  ── 병렬 실행
      │                              │                │
      └──────────────────────────────┘
      │
      ▼
[3. valuation]            ── 순차 실행
      │
      ▼
[4. report_generator]     ── 순차 실행
      │
      ▼
[최종 리포트 DB 저장]
```

### AgentState (상태 객체)

모든 노드가 공유하는 단일 상태 객체:

| 필드 | 타입 | 설명 |
|------|------|------|
| `analysis_id` | `str` | 분석 작업 ID |
| `file_paths` | `list[str]` | 업로드된 PDF 파일 경로들 |
| `registry` | `RegistryExtraction?` | 등기부등본 파싱 결과 |
| `appraisal` | `AppraisalExtraction?` | 감정평가서 파싱 결과 |
| `sale_item` | `SaleItemExtraction?` | 매각물건명세서 파싱 결과 |
| `status_report` | `StatusReportExtraction?` | 현황조사보고서 파싱 결과 |
| `rights_analysis` | `RightsAnalysisResult?` | 권리분석 결과 |
| `market_data` | `MarketDataResult?` | 시세분석 결과 |
| `news_analysis` | `NewsAnalysisResult?` | 뉴스분석 결과 |
| `valuation` | `ValuationResult?` | 가치평가 결과 |
| `report` | `dict?` | 최종 리포트 |
| `errors` | `list[str]` | 누적 에러 목록 |

### 노드 상세

#### 노드 1: document_parser (문서 파싱)

**입력**: PDF 파일 경로 목록
**출력**: registry, appraisal, sale_item, status_report

**처리 흐름**:
1. 각 PDF에서 텍스트 추출 (`pdfplumber`, 50자 미만이면 OCR 폴백)
2. Claude AI로 문서 유형 분류 (6가지 유형)
3. 분류된 유형에 따라 구조화된 데이터 추출

**문서 분류 기준** (Claude AI 판별):

| 문서 유형 | 코드명 | 판별 기준 |
|-----------|--------|-----------|
| 등기부등본 | `registry` | 갑구/을구 관련 내용, 소유권, 근저당권 등 |
| 감정평가서 | `appraisal` | 감정가, 토지가, 건물가 등 |
| 매각물건명세서 | `sale_item` | 사건번호, 점유관계, 인수할 권리 등 |
| 현황조사보고서 | `status_report` | 조사일, 점유상태, 건물상태 등 |
| 사건송달내역 | `case_notice` | 사건 관련 송달 정보 |
| 복합문서 (경매포털) | `auction_summary` | 여러 문서가 혼합된 경매 포털 페이지 (경매, 매각기일, 최저매각가격, 감정가, 건물등기, 임차인 현황 키워드 또는 tankauction/ggi/goodauction URL 포함) |

**복합문서(auction_summary) 특수 처리**:
- 하나의 PDF에 여러 문서 유형이 혼합된 경우
- registry, appraisal, sale_item, status_report 추출을 모두 시도
- 각 추출이 독립적으로 실패해도 나머지는 계속 진행 (부분 성공 허용)

**추출 데이터 구조**:

##### RegistryExtraction (등기부등본)
| 필드 | 타입 | 설명 |
|------|------|------|
| `property_address` | `str` | 소재지 |
| `property_type` | `str` | 부동산 유형 (아파트/다세대/오피스텔 등) |
| `area` | `float?` | 전용면적 (㎡) |
| `building_name` | `str?` | 건물/단지명 |
| `owner` | `str?` | 소유자 |
| `section_a_entries` | `list[RightEntry]` | 갑구 (소유권 관련) |
| `section_b_entries` | `list[RightEntry]` | 을구 (제한물권 관련) |

##### RightEntry (권리 항목)
| 필드 | 타입 | 설명 |
|------|------|------|
| `order` | `int` | 순위번호 |
| `right_type` | `str` | 권리 유형 (근저당, 전세권, 가압류 등) |
| `holder` | `str` | 권리자 |
| `amount` | `int?` | 채권액 (원) |
| `registration_date` | `str?` | 설정일 (YYYY-MM-DD) |

##### AppraisalExtraction (감정평가서)
| 필드 | 타입 | 설명 |
|------|------|------|
| `appraised_value` | `int` | 감정가 (원) |
| `land_value` | `int?` | 토지 감정가 |
| `building_value` | `int?` | 건물 감정가 |
| `land_area` | `float?` | 토지면적 (㎡, 대지권 면적) |
| `building_area` | `float?` | 건물면적 (㎡, 전용면적) |

##### SaleItemExtraction (매각물건명세서)
| 필드 | 타입 | 설명 |
|------|------|------|
| `case_number` | `str` | 사건번호 (예: 2025타경33712) |
| `property_address` | `str` | 소재지 |
| `occupancy_info` | `list[OccupancyInfo]` | 점유 관계 목록 |
| `assumed_rights` | `list[str]` | 인수할 권리 목록 |
| `special_conditions` | `list[str]` | 특별매각조건 목록 |

##### OccupancyInfo (점유자 정보)
| 필드 | 타입 | 설명 |
|------|------|------|
| `occupant_name` | `str` | 점유자명 |
| `occupant_type` | `str` | 유형 (임차인/소유자/기타) |
| `deposit` | `int?` | 보증금 (원) |
| `monthly_rent` | `int?` | 월세 (원) |
| `move_in_date` | `str?` | 전입일 (YYYY-MM-DD) |

##### StatusReportExtraction (현황조사보고서)
| 필드 | 타입 | 설명 |
|------|------|------|
| `investigation_date` | `str?` | 조사일자 |
| `property_address` | `str` | 소재지 |
| `current_occupant` | `str?` | 현 점유자 |
| `occupancy_status` | `str?` | 점유 상태 (거주중/공실/영업중 등) |
| `building_condition` | `str?` | 건물 상태 (양호/보통/불량) |
| `access_road` | `str?` | 접근도로 상태 |
| `surroundings` | `str?` | 주변 환경 |
| `special_notes` | `list[str]` | 특이사항 목록 |

---

#### 노드 2a: rights_analysis (권리분석)

> [상세 기준은 2.4절 참조](#24-권리분석-상세-기준)

**입력**: registry, sale_item
**출력**: RightsAnalysisResult

---

#### 노드 2b: market_data (시세분석)

> [상세 기준은 2.3절 참조](#23-시세-추이-분석)

**입력**: registry (주소, 면적, 부동산유형)
**출력**: MarketDataResult

---

#### 노드 2c: news_analysis (뉴스분석)

> [상세 기준은 2.5절 참조](#25-뉴스시장동향-분석)

**입력**: registry (주소, 건물명)
**출력**: NewsAnalysisResult

---

#### 노드 3: valuation (가치평가)

> [상세 기준은 2.1절, 2.2절 참조](#21-투자-추천-생성-기준)

**입력**: rights_analysis, market_data, news_analysis, appraisal, registry
**출력**: ValuationResult

---

#### 노드 4: report_generator (보고서 생성)

> [상세 구조는 2.6절 참조](#26-최종-리포트-구조)

**입력**: 모든 분석 결과
**출력**: 최종 리포트 JSON

## 1.6 외부 API 연동

### 1.6.1 Anthropic Claude API

- **모델**: `claude-sonnet-4-5-20250929`
- **용도**: 문서 분류, 데이터 추출, 권리분석, 뉴스 분석, 리포트 생성
- **호출 방식**: `AsyncAnthropic` 클라이언트 (싱글턴 패턴)
- **응답 파싱**: JSON 코드블록 → 중괄호 패턴 → 전체 텍스트 순으로 파싱 시도

### 1.6.2 국토교통부 실거래가 API

- **Base URL**: `https://apis.data.go.kr/1613000`
- **인증**: `serviceKey` 쿼리 파라미터 (percent-encoding 처리)
- **타임아웃**: 30초
- **응답 형식**: XML
- **페이지 크기**: 1,000건/요청

**지원 API 엔드포인트**:

| 부동산유형 | 매매 | 전월세 |
|-----------|------|--------|
| 아파트 | `/RTMSDataSvcAptTrade/` | `/RTMSDataSvcAptRent/` |
| 연립다세대 | `/RTMSDataSvcRHTrade/` | `/RTMSDataSvcRHRent/` |
| 단독다가구 | `/RTMSDataSvcSHTrade/` | `/RTMSDataSvcSHRent/` |
| 오피스텔 | `/RTMSDataSvcOffiTrade/` | `/RTMSDataSvcOffiRent/` |

**부동산 유형 매핑**:
- `아파트`, `공동주택` → 아파트
- `연립`, `다세대`, `빌라` → 연립다세대
- `단독`, `다가구` → 단독다가구
- `오피스텔` → 오피스텔
- 기본값: `아파트`

### 1.6.3 네이버 뉴스 검색 API

- **URL**: `https://openapi.naver.com/v1/search/news.json`
- **인증**: `X-Naver-Client-Id`, `X-Naver-Client-Secret` 헤더
- **타임아웃**: 15초
- **정렬**: `date` (최신순)
- **최대 결과**: 쿼리당 20건

### 1.6.4 주소 → 법정동코드 변환

로컬 딕셔너리 기반 변환 (외부 API 호출 없음):

- **서울특별시**: 25개 구 지원
- **경기도**: 37개 시/구 지원
- **광역시**: 부산(16), 대구(8), 인천(8), 광주(5), 대전(5), 울산(5), 세종(1)
- **매칭 로직**: 가장 긴 키워드 우선 매칭 (구 단위 > 시 단위)

## 1.7 WebSocket 실시간 통신

### 연결 관리

- **엔드포인트**: `ws://host/ws/analyses/{analysis_id}`
- **ConnectionManager**: `analysis_id` 기준으로 연결 그룹 관리
- **다중 클라이언트**: 하나의 분석에 여러 클라이언트 동시 연결 가능
- **Stale 연결 자동 제거**: 전송 실패 시 연결 자동 해제

### 메시지 유형

| type | 설명 | 데이터 |
|------|------|--------|
| `status_update` | 단계별 진행 상태 | `{stage, status, progress}` |
| `analysis_complete` | 분석 완료 | `{status, report_url}` |
| `analysis_error` | 분석 오류 | `{error}` |

### 진행 단계 (stages)

| 단계 코드 | 설명 | 진행률 |
|-----------|------|--------|
| `parsed_documents` | 문서 파싱 | 0 → 100 |
| `rights_analysis` | 권리분석 | 0 → 100 |
| `market_data` | 시세분석 | 0 → 100 |
| `news_analysis` | 뉴스분석 | 0 → 100 |
| `valuation` | 가치평가 | 0 → 100 |
| `report` | 리포트 생성 | 0 → 100 |

## 1.8 에러 처리 및 재시도

### 노드 재시도 정책

- **최대 재시도**: 3회
- **백오프 방식**: 지수 백오프 (1초 → 2초 → 4초)
- **최종 실패 시**: 에러 메시지를 `state.errors`에 추가하고 계속 진행

### Graceful Degradation (부분 실패 허용)

- 병렬 노드(권리분석/시세분석/뉴스분석) 중 일부가 실패해도 나머지 결과로 가치평가 진행
- 시세 데이터 없으면 감정가로 폴백
- 감정가도 없으면 가치평가 스킵 + 에러 기록
- 보고서는 사용 가능한 데이터만으로 생성

---

# 2. 리포트 생성 요구사항

## 2.1 투자 추천 생성 기준

### 추천 판단 로직

투자 추천은 **위험도**, **예상 수익률(ROI)**, **인수 위험** 3가지 기준으로 결정됩니다.

#### 추천 등급 판정 기준

| 추천 등급 | 조건 | 사유 메시지 |
|-----------|------|-------------|
| **추천** (`recommend`) | 위험도 LOW **AND** ROI ≥ 15% **AND** 인수위험 없음 | "위험도 낮고 예상 수익률 {roi}%로 양호합니다." |
| **비추천** (`not_recommend`) | 위험도 HIGH **OR** ROI < 5% **OR** 인수위험 있음 | "위험도가 높거나 수익률이 낮습니다." |
| **보류** (`hold`) | 상기 조건에 해당하지 않는 경우 | "추가 검토가 필요합니다." |

#### 판정 입력값 상세

| 입력값 | 산출 근거 | 설명 |
|--------|-----------|------|
| `risk_level` | 권리분석 결과의 `risk_level` | Claude AI가 종합 평가한 위험 등급 (high/medium/low) |
| `roi_moderate` | 가치평가 엔진의 적정 수익률 | (적정매도가 - 총투자비) / 총투자비 × 100 |
| `has_assumed_risk` | 권리분석 결과의 `total_assumed_amount > 0` | 인수해야 할 권리(선순위 권리)가 있는지 여부 |

#### 추천 판정 우선순위

1. **비추천 조건이 하나라도 해당** → 비추천 (가장 우선)
2. **추천 조건 모두 충족** → 추천
3. **나머지** → 보류

### 투자 추천 사유 (reasoning) 생성

valuation 노드에서 아래 5개 항목을 순서대로 조합하여 생성:

1. **추정 시세 근거**: 실거래 평균 평당가 × 면적 = 추정시세 (또는 감정가 폴백)
2. **입찰 적정가 근거**: 추정 시세의 65~85%에서 부대비용과 인수권리 차감
3. **매도 적정가 근거**: 추정 시세에 시세추이(±3%)와 호재/악재(±2%) 반영
4. **예상 수익률**: 적정입찰가 → 적정매도가 기준 ROI
5. **최종 판정 사유**: 추천/보류/비추천 판정 근거 문장

## 2.2 가격 분석 기준

### 2.2.1 입찰적정가 산출 근거

입찰적정가는 **추정 시세** 대비 할인율을 적용하고, **부대비용**과 **인수권리금액**을 차감하여 산출합니다.

#### 추정 시세 결정 (우선순위)

| 순위 | 조건 | 산출 방식 |
|------|------|-----------|
| 1 | 시장 데이터 존재 + 면적 정보 있음 | `평균 평당가 × (전용면적 ÷ 3.305785)` |
| 2 | 감정평가서 존재 | 감정가 그대로 사용 |
| 3 | 둘 다 없음 | **가치평가 불가** (에러 반환) |

#### 입찰적정가 3단계

| 단계 | 할인율 | 산출 공식 |
|------|--------|-----------|
| **보수적** (conservative) | 시세의 65% | `추정시세 × 0.65 - (인수권리금액 + 부대비용)` |
| **적정** (moderate) | 시세의 75% | `추정시세 × 0.75 - (인수권리금액 + 부대비용)` |
| **공격적** (aggressive) | 시세의 85% | `추정시세 × 0.85 - (인수권리금액 + 부대비용)` |

- **최저가 보장**: 각 단계의 산출 결과가 최저매각가격보다 낮으면 최저매각가격으로 상향
- **차감 항목**: 인수권리금액(선순위 근저당 등) + 부대비용(취득세+등록비+법무사비+명도비)

#### 부대비용 산출

| 비용 항목 | 산출 기준 |
|-----------|-----------|
| **취득세** | 아래 취득세 표 참조 |
| **등록 수수료** | 취득세의 20% |
| **법무사 비용** | 고정 800,000원 |
| **명도 비용** | 대항력 있는 임차인: 500만원/인, 없는 임차인: 200만원/인 |
| **중개 수수료** | 입찰가의 0.4% (비용 합계에는 미포함) |
| **수선비** | 0원 (미구현) |
| **양도소득세** | 0원 (미구현) |

#### 취득세율표

| 부동산 유형 | 가격 구간 | 세율 |
|-------------|-----------|------|
| 상가/오피스텔 | 전 구간 | 4.6% |
| 토지 | 전 구간 | 4.0% |
| 주택 (3주택 이상) | 전 구간 | 8.0% |
| 주택 (2주택) | 전 구간 | 8.0% |
| 주택 (1주택) | 6억 이하 | 1.0% |
| 주택 (1주택) | 6억~9억 | 1.0% + (가격-6억)/3억 × 2% (누진) |
| 주택 (1주택) | 9억 초과 | 3.0% |

> 현재 1주택 기준으로만 계산됩니다 (`num_houses=1` 기본값).

### 2.2.2 매도적정가 산출 근거

매도적정가는 **추정 시세**에 **시세 추이 보정**과 **호재/악재 보정**을 적용하여 산출합니다.

#### 보정 계수

| 보정 요인 | 조건 | 보정값 |
|-----------|------|--------|
| **시세 추이** (trend) | 상승 | +3% |
| | 하락 | -3% |
| | 보합 | 0% |
| **호재** (positive) | 긍정 뉴스 요인 존재 | +2% |
| **악재** (negative) | 부정 뉴스 요인 존재 | -2% |

#### 매도적정가 3단계

| 단계 | 기준 계수 | 산출 공식 |
|------|-----------|-----------|
| **비관적** (conservative) | 0.95 | `추정시세 × (0.95 + 추이보정 + 호재보정)` |
| **기본** (moderate) | 1.00 | `추정시세 × (1.00 + 추이보정 + 호재보정)` |
| **낙관적** (aggressive) | 1.07 | `추정시세 × (1.07 + 추이보정 + 호재보정)` |

#### 매도적정가 산출 예시

추정 시세 10억, 상승추세, 호재 있음, 악재 없음인 경우:
- 보정: +3% (상승) +2% (호재) = +5%
- 비관적: 10억 × (0.95 + 0.05) = 10억
- 기본: 10억 × (1.00 + 0.05) = 10.5억
- 낙관적: 10억 × (1.07 + 0.05) = 11.2억

### 2.2.3 수익률(ROI) 산출

```
총투자비 = 적정입찰가(moderate) + 부대비용 합계
ROI = (매도적정가 - 총투자비) / 총투자비 × 100
연환산 ROI = ROI ÷ (보유기간개월 / 12)
```

- **기본 보유기간**: 12개월
- **ROI 산출 기준**: 적정(moderate) 입찰가 + 비용 → 적정(moderate) 매도가
- 보수적/낙관적 ROI도 함께 산출

## 2.3 시세 추이 분석

### 데이터 수집

1. 등기부등본에서 **주소**, **전용면적**, **부동산유형** 추출
2. 주소를 **법정동코드**(LAWD_CD, 5자리)로 변환
3. 국토교통부 API로 **최근 12개월** 매매 + 전월세 실거래 데이터 수집

### 매매 거래 필터링

| 단계 | 조건 | 폴백 |
|------|------|------|
| 1차 | 면적 ±10% 이내 | → 2차 |
| 2차 | 면적 ±30% 이내 | → 3차 |
| 3차 | 전체 거래 (필터 없음) | - |

**아파트 추가 필터링**: 건물명(단지명)이 2자 이상이면 건물명 기준 양방향 부분 매칭 적용. 필터 결과가 3건 미만이면 폴백.

### 시세 추이 판단 기준

| 조건 | 분류 | 비교 방식 |
|------|------|-----------|
| 변화율 > +3% | **상승** | 최근 6개월 평균 vs 이전 6개월 평균 |
| 변화율 < -3% | **하락** | 동일 |
| -3% ≤ 변화율 ≤ +3% | **보합** | 동일 |

- 데이터가 12개월 미만이면 중간 지점 기준으로 분할
- 월별 평균가를 산출하여 비교

### 전월세 분석

| 항목 | 산출 방식 |
|------|-----------|
| **전세 비율** | 평균전세보증금 / 매매평균가 |
| **평균 전세** | 전세 거래(월세=0 & 보증금>0) 보증금의 평균 |
| **평균 월세** | 월세 거래(월세>0)의 월 임대료 평균 |

### MarketDataResult 출력 구조

| 필드 | 타입 | 설명 |
|------|------|------|
| `recent_transactions` | `list[Transaction]` | 최근 매매 거래 (최대 20건) |
| `recent_rent_transactions` | `list[RentTransaction]` | 최근 전월세 거래 (최대 20건) |
| `avg_price_per_pyeong` | `int` | 평균 평당가 (원) |
| `price_range_low` | `int` | 가격 하한 |
| `price_range_high` | `int` | 가격 상한 |
| `price_trend` | `str` | 시세 추이 (상승/보합/하락) |
| `jeonse_ratio` | `float` | 전세가율 |
| `avg_jeonse_deposit` | `int` | 평균 전세 보증금 |
| `avg_monthly_rent` | `int` | 평균 월세 |
| `appraisal_vs_market_gap` | `float` | 감정가 대비 시세 괴리율 |
| `confidence_score` | `float` | 신뢰도 (거래건수/10, 최대 1.0) |

### 단위 변환

- **평 → ㎡**: `1평 = 3.305785 ㎡`
- **만원 → 원**: API 응답의 금액은 만원 단위 → `× 10,000`으로 원 단위 변환

## 2.4 권리분석 상세 기준

### 2.4.1 등기부등본상의 하자 파악 기준

#### 말소기준권리 판단

**말소기준권리**란 경매로 소멸되는 권리와 인수되는 권리를 구분하는 기준이 되는 권리입니다.

**판단 로직**:
1. 갑구(소유권 관련) + 을구(제한물권) 전체 권리를 수집
2. 아래 **말소기준권리 대상 유형**에 해당하는 권리만 필터링
3. `registration_date`(설정일)이 있는 권리만 대상
4. 설정일 기준 **가장 이른 날짜**의 권리가 말소기준권리

**말소기준권리 대상 유형** (EXTINGUISHMENT_ELIGIBLE_TYPES):

| 유형 | 설명 |
|------|------|
| `근저당권` / `근저당권설정` | 금융기관 담보대출 설정 |
| `전세권` / `전세권설정` | 전세권 등기 |
| `가압류` | 가압류 등기 |
| `담보가등기` | 담보 목적 가등기 |
| `압류` | 압류 등기 |
| `경매기입등기` | 경매개시결정 등기 |

**말소기준권리 없는 경우**: 위험도 `HIGH`로 설정, "말소기준권리를 특정할 수 없어 위험도가 높습니다" 경고, 신뢰도 0.3

#### 권리 인수/소멸 분류

말소기준권리의 설정일(`basis_date`)을 기준으로 각 권리를 분류:

| 조건 | 분류 | 설명 |
|------|------|------|
| `registration_date < basis_date` | **인수** (assumed) | 낙찰자가 인수해야 하는 권리 |
| `registration_date >= basis_date` | **소멸** (extinguished) | 경매로 자동 소멸되는 권리 |
| `registration_date` 없음 | **소멸** 처리 | 날짜 불명 시 소멸로 간주 |

**예외**: `소유권이전`, `소유권보존`은 인수/소멸 분류에서 제외 (소유권 변경은 부채가 아님)

#### Claude AI 종합 위험도 평가

규칙 기반 분석 이후 Claude AI가 **특수 권리 위험**을 추가 평가합니다.

**AI가 추가 탐지하는 특수 위험**:

| 특수 권리 | 설명 |
|-----------|------|
| `가처분` | 법원의 처분금지 가처분 |
| `유치권` | 물건에 대한 유치권 주장 |
| `법정지상권` | 법정지상권 성립 가능성 |
| `예고등기` | 예고등기에 의한 권리 불안정 |
| `신탁등기` | 신탁재산 관련 복잡성 |

**AI 출력**:
- `risk_level`: high / medium / low
- `risk_factors`: 구체적 위험 요인 목록
- `confidence`: 분석 신뢰도 (0.0~1.0)
- `warnings`: 경고 사항 목록

### 2.4.2 매각물건명세서상의 하자 파악 기준

#### 임차인 분석

매각물건명세서의 `occupancy_info`를 기반으로 임차인별 대항력과 우선변제권을 분석:

**대항력 판단**:
- 조건: `전입일(move_in_date) < 말소기준권리 설정일(basis_date)`
- 의미: 대항력이 있는 임차인은 낙찰자에게 보증금 반환을 요구할 수 있음

**우선변제권 판단**:
- 조건: **대항력 있음** AND `보증금 ≤ 165,000,000원` (서울 기준 소액임차인 기준)
- 의미: 매각대금에서 우선 변제받을 수 있는 권리

**소액임차인 최우선변제 기준**: `165,000,000원` (서울특별시 기준, 현재 하드코딩)

| 분석 항목 | 판정 기준 |
|-----------|-----------|
| 소유자 | 임차인 분석 대상에서 **제외** |
| 대항력 있는 임차인 | 전입일 < 말소기준권리일 |
| 소액임차인 (우선변제) | 대항력 있음 + 보증금 ≤ 1.65억 |
| 일반 임차인 | 대항력 없음 (소멸되는 임차권) |

#### 인수할 권리 및 특별매각조건

매각물건명세서에서 추출하는 추가 정보:
- `assumed_rights`: 법원이 명시한 인수해야 할 권리 목록
- `special_conditions`: 특별매각조건 (해당 시)

### 2.4.3 말소기준권리 기준의 하자 파악 기준

#### 종합 위험도 결정 흐름

```
1. 말소기준권리 판단
   ├── 말소기준권리 없음 → 위험도 HIGH (즉시 반환)
   └── 말소기준권리 있음 → 계속
       │
2. 인수/소멸 분류 (규칙 기반)
   ├── 인수할 권리 목록 산출
   ├── 소멸할 권리 목록 산출
   └── 인수 총액 산출
       │
3. 임차인 분석 (규칙 기반)
   ├── 대항력 보유 여부 판정
   └── 우선변제권 보유 여부 판정
       │
4. Claude AI 종합 평가
   ├── 특수 권리 위험 탐지
   ├── 전체 위험도 판정 (high/medium/low)
   └── 구체적 위험 요인 + 경고사항 생성
```

#### RightsAnalysisResult 출력 구조

| 필드 | 타입 | 설명 |
|------|------|------|
| `extinguishment_basis` | `str` | 말소기준권리 설명 |
| `assumed_rights` | `list[str]` | 인수할 권리 목록 |
| `extinguished_rights` | `list[str]` | 소멸할 권리 목록 |
| `tenants` | `list[TenantAnalysis]` | 임차인 분석 결과 |
| `risk_level` | `RiskLevel` | 위험도 (HIGH/MEDIUM/LOW) |
| `risk_factors` | `list[str]` | 위험 요인 + 경고사항 |
| `total_assumed_amount` | `int` | 인수 총액 (원) |
| `confidence_score` | `float` | 분석 신뢰도 |

## 2.5 뉴스/시장동향 분석

### 뉴스 검색 키워드 자동 생성

등기부등본의 주소에서 자동으로 검색 키워드를 생성합니다:

| 주소 요소 | 생성 키워드 |
|-----------|-------------|
| `{구}` 발견 시 | `{구} 부동산 시장`, `{구} 재개발 재건축`, `{구} 개발 호재`, `{구} 부동산 전망` |
| `{동}` 발견 시 | `{동} 부동산`, `{동} 개발` |
| `{시}` 발견 (구 없음) | `{시} 부동산 시장`, `{시} 부동산 전망`, `{시} 개발 호재` |
| `{시}` + `{구}` 있음 | `{시} 부동산 전망` 추가 |
| 건물명(단지명) 있음 | `{건물명} 시세` |

### 뉴스 수집 및 전처리

1. 생성된 키워드별 네이버 뉴스 API 호출 (쿼리당 최대 10건)
2. 개별 키워드 실패 시 해당 키워드만 스킵하고 계속
3. HTML 태그 제거 후 제목 기준 **중복 제거**
4. 최대 30건의 고유 뉴스를 Claude AI에 전달

### Claude AI 뉴스 분석

AI가 각 뉴스에 대해 분석:

| 항목 | 설명 |
|------|------|
| `sentiment` | positive / negative / neutral |
| `impact_score` | 0~10 (부동산 가치 영향도) |
| `summary` | 1~2문장 핵심 요약 |

종합 분석:

| 항목 | 설명 |
|------|------|
| `positive_factors` | 호재 요인 목록 |
| `negative_factors` | 악재 요인 목록 |
| `area_attractiveness_score` | 지역 매력도 (0~100) |
| `investment_opinion` | 종합 투자 의견 (3~5문장) |
| `outlook` | 6개월 전망 (긍정/중립/부정) |
| `market_trend_summary` | 시장 동향 요약 (2~3문장) |

### Sentiment 매핑

| LLM 출력값 | 변환 결과 |
|-----------|-----------|
| `positive`, `호재` | `POSITIVE` |
| `negative`, `악재` | `NEGATIVE` |
| `neutral`, `중립`, 기타 | `NEUTRAL` |

## 2.6 최종 리포트 구조

### Claude AI 생성 분석 요약 (analysis_summary)

Claude AI가 모든 분석 결과를 종합하여 7개 섹션의 자연어 요약을 생성합니다:

| 섹션 | 내용 | 분량 |
|------|------|------|
| `property_overview` | 물건 개요 (유형, 위치, 면적, 감정가) | 2~3문장 |
| `rights_summary` | 권리분석 요약 (말소기준, 인수권리, 대항력, 위험도) | 3~5문장 |
| `market_summary` | 시세분석 요약 (실거래가, 감정가 대비 수준, 추이) | 3~5문장 |
| `news_summary` | 뉴스/동향 요약 (호재/악재, 개발계획, 전망) | 3~5문장 |
| `bid_price_reasoning` | 입찰적정가 산출 근거 | 3~5문장 |
| `sale_price_reasoning` | 매도적정가 산출 근거 | 3~5문장 |
| `overall_opinion` | 종합 투자 의견 | 5~7문장 |

### 최종 리포트 JSON 구조

```json
{
  "analysis_summary": {
    "property_overview": "...",
    "rights_summary": "...",
    "market_summary": "...",
    "news_summary": "...",
    "bid_price_reasoning": "...",
    "sale_price_reasoning": "...",
    "overall_opinion": "..."
  },
  "recommendation": "recommend | hold | not_recommend",
  "reasoning": "상세 산출 근거 (5단계 조합 텍스트)",
  "risk_summary": "위험도: {level} (요인1, 요인2, ...)",
  "bid_price": {
    "conservative": 650000000,
    "moderate": 750000000,
    "aggressive": 850000000
  },
  "sale_price": {
    "conservative": 950000000,
    "moderate": 1000000000,
    "aggressive": 1070000000
  },
  "expected_roi": 33.3,
  "cost_breakdown": {
    "acquisition_tax": 7500000,
    "registration_fee": 1500000,
    "legal_fee": 800000,
    "eviction_cost": 5000000,
    "repair_cost": 0,
    "capital_gains_tax": 0
  },
  "confidence_score": 0.8,
  "valuation": { /* 전체 ValuationResult 객체 */ },
  "chart_data": [
    { "date": "2025-06", "price": 950000000 },
    { "date": "2025-07", "price": 960000000 }
  ],
  "disclaimer": "본 분석은 AI가 생성한 참고 자료이며, 실제 투자 결정 시 법률·세무 전문가의 자문을 별도로 받으시기 바랍니다."
}
```

### 차트 데이터

- `chart_data`: 최근 매매 거래 내역에서 추출 (최대 20건)
- 각 항목: `{date: "YYYY-MM", price: 원단위금액}`
- 시세 추이 차트에 활용

---

# 3. FE 구현사항

## 3.1 기술 스택

| 항목 | 기술 | 버전 |
|------|------|------|
| 프레임워크 | React | 19.2 |
| 언어 | TypeScript | 5.9 |
| 빌드 | Vite | 7.3 |
| CSS | Tailwind CSS | 4.1 |
| 라우팅 | React Router DOM | 7.13 |
| 상태 관리 | TanStack React Query | 5.90 |
| HTTP | Axios | 1.13 |
| 차트 | Recharts | 3.7 |

## 3.2 페이지 구성

### 라우팅 구조

| 경로 | 컴포넌트 | 설명 |
|------|----------|------|
| `/` | `Home` | 홈 - 파일 업로드 + 분석 시작 |
| `/analysis/:id` | `AnalysisProgress` | 분석 진행 상황 (실시간) |
| `/report/:id` | `Report` | 분석 리포트 (탭 기반) |
| `/history` | `History` | 분석 이력 목록 |

### 페이지별 상세

#### Home (홈 페이지)

- **파일 드래그 앤 드롭 업로드** (PDF만 허용)
- **사건번호** 및 **설명** 입력 필드 (선택)
- 업로드된 파일 목록 표시 (파일명, 크기, 삭제 버튼)
- "분석 시작" 버튼 → API 호출 후 분석 진행 페이지로 이동

#### AnalysisProgress (분석 진행)

- **WebSocket** 연결로 실시간 진행 상태 수신
- 6단계 진행 트래커 표시:
  - 문서 파싱 → 권리분석 → 시세분석 → 뉴스분석 → 가치평가 → 리포트 생성
- 단계별 상태: pending(대기) → running(진행중) → done(완료) / error(오류)
- 전체 진행률 표시 (0~100%)
- 완료 시 자동으로 리포트 페이지 이동
- 오류 시 에러 메시지 표시

#### Report (분석 리포트)

**탭 기반 구조**:

| 탭 | 컴포넌트 | 내용 |
|----|----------|------|
| 개요 | `RecommendationCard` + `PriceRangeCard` + `PriceChart` | 추천/가격/차트 |
| 권리분석 | `RightsAnalysisTab` | 말소기준/인수권리/임차인 |
| 시세분석 | `MarketDataTab` | 거래내역/전월세 |
| 비용분석 | `CostBreakdownTab` | 비용 상세 |
| 뉴스 | `NewsTab` | 뉴스/동향 |

상단에 **면책 배너** (`DisclaimerBanner`) 항상 표시.

#### History (분석 이력)

- 과거 분석 작업 목록 (최신순)
- 각 항목: ID, 상태 뱃지, 설명, 사건번호, 생성일
- 클릭 시 해당 리포트 페이지로 이동

## 3.3 컴포넌트 구조

### 업로드 관련

| 컴포넌트 | 설명 |
|----------|------|
| `UploadForm` | 전체 업로드 폼 (파일 드랍존 + 파일 목록 + 입력 필드 + 제출 버튼) |
| `FileDropzone` | 드래그 앤 드롭 영역 (PDF 허용, 클릭 또는 드래그로 파일 선택) |
| `FileList` | 업로드 대기 파일 목록 (파일명, 크기 표시, 삭제 기능) |

### 분석 관련

| 컴포넌트 | 설명 |
|----------|------|
| `ProgressTracker` | 6단계 진행 트래커 (아이콘 + 상태 색상 + 진행률 바) |

### 리포트 관련

| 컴포넌트 | Props | 설명 |
|----------|-------|------|
| `RecommendationCard` | `recommendation`, `reasoning`, `confidenceScore?` | 투자 추천 뱃지 (추천/보류/비추천) + 사유 + 신뢰도 바 |
| `PriceRangeCard` | `bidPrice`, `salePrice`, `minimumSalePrice?` | 입찰적정가 3단계 + 매도적정가 3단계 + 최저매각가격 |
| `PriceChart` | `chartData`, `appraisedValue?` | 시세 추이 라인차트 (Recharts) + 감정가 기준선 (점선) |
| `RightsAnalysisTab` | `data` | 말소기준권리, 위험도 뱃지, 인수/소멸 권리 목록, 임차인 테이블, 위험요인 |
| `MarketDataTab` | `data` | 거래 내역 테이블, 시세 통계 |
| `CostBreakdownTab` | `data` | 비용 항목별 상세 표 |
| `NewsTab` | `data` | 뉴스 목록, 감성 뱃지, 호재/악재 요인 |
| `DisclaimerBanner` | - | "AI 생성 참고자료" 면책 배너 |

### 공통 컴포넌트

| 컴포넌트 | 설명 |
|----------|------|
| `Header` | 상단 네비게이션 바 (AuctionAI 로고 + 홈/분석이력 링크) |
| `LoadingSkeleton` | 로딩 스켈레톤 UI |
| `Spinner` | 로딩 스피너 (SVG 애니메이션) |
| `ErrorMessage` | 에러 메시지 표시 (아이콘 + 텍스트) |

### 추천 등급 UI 표현

| 등급 | 뱃지 라벨 | 배경색 | 텍스트색 |
|------|-----------|--------|----------|
| `recommend` | 추천 | `bg-green-100` | `text-green-800` |
| `hold` | 보류 | `bg-yellow-100` | `text-yellow-800` |
| `not_recommend` | 비추천 | `bg-red-100` | `text-red-800` |

### 위험도 UI 표현

| 위험도 | 배경색 | 텍스트색 |
|--------|--------|----------|
| `HIGH` | `bg-red-100` | `text-red-800` |
| `MEDIUM` | `bg-yellow-100` | `text-yellow-800` |
| `LOW` | `bg-green-100` | `text-green-800` |

### 금액 포맷팅

모든 금액은 한국식으로 포맷팅:
- `≥ 1억`: `{N}억 {M}만원` (예: `3억 5,000만원`)
- `≥ 1만`: `{N}만원` (예: `5,000만원`)
- `< 1만`: `{N}원`

## 3.4 상태 관리 및 데이터 흐름

### Custom Hooks

#### useFileUpload

| 반환값 | 타입 | 설명 |
|--------|------|------|
| `files` | `File[]` | 선택된 파일 목록 |
| `addFiles` | `(files: File[]) => void` | 파일 추가 |
| `removeFile` | `(index: number) => void` | 파일 제거 |

#### useAnalysis

- TanStack React Query 기반 데이터 페칭
- 분석 목록 조회, 상세 조회, 리포트 조회
- 분석 생성 mutation

#### useWebSocket

| 반환값 | 타입 | 설명 |
|--------|------|------|
| `status` | `string` | 현재 분석 상태 |
| `progress` | `AnalysisProgress` | 단계별 진행 상태 |
| `isConnected` | `boolean` | WebSocket 연결 상태 |

- 자동 연결/해제 (컴포넌트 마운트/언마운트)
- 메시지 수신 시 상태 자동 업데이트

### API 클라이언트

- **Base URL**: `http://localhost:8000`
- Axios 인스턴스 사용
- 엔드포인트: `/api/v1/analyses`, `/api/v1/files`

## 3.5 타입 시스템

### 핵심 타입 정의

```typescript
type AnalysisStatus = 'pending' | 'running' | 'done' | 'error'
type StageStatus = 'pending' | 'running' | 'done' | 'error'
type Recommendation = 'recommend' | 'hold' | 'not_recommend'

interface AnalysisProgress {
  overall: number
  stages: {
    parsed_documents: StageProgress
    rights_analysis: StageProgress
    market_data: StageProgress
    news_analysis: StageProgress
    valuation: StageProgress
    report: StageProgress
  }
}

interface AnalysisReport {
  recommendation: Recommendation
  reasoning: string
  risk_summary: string
  bid_price: { conservative: number; moderate: number; aggressive: number }
  sale_price: { conservative: number; moderate: number; aggressive: number }
  expected_roi: number
  cost_breakdown?: Record<string, number>
  confidence_score?: number
  disclaimer?: string
  chart_data?: { price_trend?: { date: string; price: number }[] }
}
```

---

# 4. 테스트 현황

## 테스트 파일 및 커버리지

| 테스트 파일 | 대상 | 테스트 항목 수 | 주요 검증 내용 |
|-------------|------|---------------|----------------|
| `test_task_02_rights_analysis.py` | 권리분석 | 6 | 말소기준권리 판단, 인수/소멸 분류, 대항력/우선변제권, Claude 연동, 노드 전체 흐름 |
| `test_task_03_market_data.py` | 시세분석 | 7 | 면적 필터링, 건물명 필터링, 시세추이 판단, 전월세 분석, API 연동, 노드 전체 흐름 |
| `test_task_04_news_analysis.py` | 뉴스분석 | 5 | 키워드 생성, 중복 제거, Sentiment 파싱, Claude 분석 연동, 에러 처리 |
| `test_task_05_valuation.py` | 가치평가 | 9 | 취득세 계산, 입찰가 3단계, ROI 산출, 추천 판정, 비용 합산, 노드 폴백 |
| `test_task_06_graph.py` | 워크플로우 | 6 | 노드 등록 검증, 실행 순서, 재시도, Graceful degradation, 리포트 생성, 유틸리티 |

## 테스트 전략

- **외부 API**: 모두 `unittest.mock` (AsyncMock)으로 모킹
- **Claude AI**: `_call_llm` 함수를 모킹하여 고정된 JSON 응답 반환
- **순수 로직**: 취득세, 입찰가, ROI 등 수치 계산은 직접 검증
- **비동기 테스트**: `@pytest.mark.asyncio` 데코레이터 사용

---

# 부록: 현재 미구현/제한사항

| 항목 | 현재 상태 | 비고 |
|------|-----------|------|
| 수선비 (repair_cost) | 0원 고정 | 추후 건물 상태 기반 추정 필요 |
| 양도소득세 (capital_gains_tax) | 0원 고정 | 추후 보유기간/다주택 기반 산출 필요 |
| 다주택자 취득세 | 1주택 기준 고정 | `num_houses` 파라미터는 있으나 미활용 |
| 소액임차인 기준 | 서울 기준 고정 (1.65억) | 지역별 기준 차등 적용 필요 |
| 보유기간 | 12개월 고정 | 사용자 입력으로 변경 가능하게 개선 필요 |
| 차트 데이터 | 최대 20건 | 더 긴 기간 지원 필요 시 확장 |
| 법정동코드 | 서울/경기/광역시만 지원 | 충청/전라/경상/강원/제주 등 추가 필요 |
| 인증/인가 | 미구현 | 사용자 인증 시스템 없음 |
| 분석 결과 PDF 출력 | 미구현 | 리포트 PDF 다운로드 기능 |
| 모바일 반응형 | 부분 지원 | Tailwind 반응형 클래스 사용 중이나 완전 최적화 필요 |
