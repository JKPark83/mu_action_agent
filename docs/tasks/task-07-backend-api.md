# Task-07: 백엔드 API 완성

> **참조 스펙**: PRD-07 전체
> **예상 작업 시간**: 3~4시간
> **선행 작업**: Task-00 (인프라), Task-06 (워크플로우)
> **변경 파일 수**: 4~5개

---

## 목차

1. [분석 작업 생성 API 완성](#1-분석-작업-생성-api-완성)
2. [진행 상태 조회 API](#2-진행-상태-조회-api)
3. [리포트 조회 API](#3-리포트-조회-api)
4. [에러 응답 통일](#4-에러-응답-통일)
5. [테스트 가이드](#5-테스트-가이드)

---

## 1. 분석 작업 생성 API 완성

### 1.1 파일 업로드 + 분석 시작 통합

> 파일: `backend/app/api/v1/analyses.py`

```python
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, UploadFile

@router.post("", status_code=201)
async def create_analysis(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    description: str | None = Form(None),
    case_number: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """
    분석 작업 생성 흐름:
    1. PDF 파일 검증 (형식, 크기, 개수)
    2. Analysis 레코드 생성 (status=pending)
    3. 각 파일을 디스크에 저장 + UploadedFile 레코드 생성
    4. BackgroundTask로 워크플로우 실행
    5. Analysis 응답 반환
    """
    # 파일 개수 제한 (최대 10개)
    if len(files) > 10:
        raise HTTPException(400, "최대 10개 파일까지 업로드 가능합니다")

    # Analysis 생성
    analysis = Analysis(
        id=str(uuid4()),
        status="pending",
        description=description,
        case_number=case_number,
    )
    db.add(analysis)

    # 파일 저장
    file_paths = []
    for file in files:
        validate_pdf(file)
        saved = await save_file(file, analysis.id, db)
        file_paths.append(saved.stored_path)

    await db.commit()

    # 백그라운드 분석 시작
    background_tasks.add_task(
        run_analysis_workflow,
        analysis.id,
        file_paths,
        get_db_session_factory(),
    )

    return AnalysisResponse.from_model(analysis)
```

### 1.2 파일 검증 함수

```python
def validate_pdf(file: UploadFile) -> None:
    if file.content_type != "application/pdf":
        raise HTTPException(400, f"PDF 파일만 허용됩니다: {file.filename}")
    if file.size and file.size > 50 * 1024 * 1024:
        raise HTTPException(413, f"파일 크기 초과 (50MB): {file.filename}")
```

---

## 2. 진행 상태 조회 API

### 2.1 상세 진행률 API

```python
@router.get("/{analysis_id}/status")
async def get_analysis_status(
    analysis_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    분석 진행 상태 조회
    - 전체 진행률 (0~100)
    - 단계별 상태 (pending/running/done/error)
    - 예상 완료 시간
    """
    analysis = await db.get(Analysis, analysis_id)
    if not analysis:
        raise HTTPException(404, "분석 작업을 찾을 수 없습니다")

    # 각 분석 결과 JSON 필드 존재 여부로 진행률 계산
    stages = {
        "document_parsing": "done" if analysis.parsed_documents else ("running" if analysis.status == "running" else "pending"),
        "rights_analysis": "done" if analysis.rights_analysis else "pending",
        "market_data": "done" if analysis.market_data else "pending",
        "news_analysis": "done" if analysis.news_analysis else "pending",
        "valuation": "done" if analysis.valuation else "pending",
        "report_generation": "done" if analysis.report else "pending",
    }

    done_count = sum(1 for s in stages.values() if s == "done")
    overall = int(done_count / len(stages) * 100)

    return {
        "id": analysis.id,
        "status": analysis.status,
        "progress": {
            "overall": overall,
            "stages": {k: {"status": v, "progress": 100 if v == "done" else 0} for k, v in stages.items()},
        },
        "started_at": analysis.started_at,
    }
```

---

## 3. 리포트 조회 API

```python
@router.get("/{analysis_id}/report")
async def get_analysis_report(
    analysis_id: str,
    db: AsyncSession = Depends(get_db),
):
    """분석 완료된 리포트 조회"""
    analysis = await db.get(Analysis, analysis_id)
    if not analysis:
        raise HTTPException(404, "분석 작업을 찾을 수 없습니다")

    if analysis.status != "done":
        raise HTTPException(400, f"분석이 완료되지 않았습니다 (현재: {analysis.status})")

    if not analysis.report:
        raise HTTPException(404, "리포트가 아직 생성되지 않았습니다")

    return analysis.report
```

---

## 4. 에러 응답 통일

### 4.1 커스텀 예외 핸들러

> 파일: `backend/app/main.py`에 추가

```python
from fastapi.responses import JSONResponse

@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail, "status_code": exc.status_code},
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    return JSONResponse(
        status_code=500,
        content={"detail": "내부 서버 오류가 발생했습니다", "status_code": 500},
    )
```

---

## 5. 테스트 가이드

### 5.1 통합 테스트 케이스

| ID | 테스트명 | 설명 | 기대 결과 |
|:---:|:---|:---|:---|
| IT-1 | `test_create_analysis_with_files` | PDF 업로드 + 분석 생성 | 201, pending |
| IT-2 | `test_create_analysis_no_files` | 파일 없이 생성 | 422 |
| IT-3 | `test_create_analysis_non_pdf` | txt 파일 업로드 | 400 |
| IT-4 | `test_create_analysis_too_many_files` | 11개 파일 | 400 |
| IT-5 | `test_get_status_pending` | 대기 중 상태 조회 | overall=0 |
| IT-6 | `test_get_report_not_done` | 미완료 리포트 조회 | 400 |
| IT-7 | `test_get_report_success` | 완료된 리포트 조회 | 200, report JSON |
| IT-8 | `test_list_analyses` | 목록 조회 | 200, 리스트 |
| IT-9 | `test_delete_analysis` | 분석 삭제 | 204 |

### 5.2 테스트 실행

```bash
cd backend
uv run pytest tests/integration/api/ -v
```

---

## 파일 변경 요약

### 수정 파일

| 파일 경로 | 변경 내용 |
|:---|:---|
| `backend/app/api/v1/analyses.py` | 생성 API 완성, status/report API 추가 |
| `backend/app/api/v1/files.py` | 디스크 저장 + 검증 로직 완성 |
| `backend/app/main.py` | 에러 핸들러 등록 |
| `backend/app/api/v1/router.py` | WebSocket 라우터 등록 |

### 신규 생성 파일

| 파일 경로 | 설명 |
|:---|:---|
| `backend/tests/integration/api/test_analyses.py` | API 통합 테스트 |
