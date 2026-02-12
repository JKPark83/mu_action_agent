# Task-08: 프론트엔드 UI 구현

> **참조 스펙**: PRD-08 전체
> **예상 작업 시간**: 8~12시간
> **선행 작업**: Task-07 (백엔드 API 완성)
> **변경 파일 수**: 10~15개

---

## 목차

1. [홈 페이지 (PDF 업로드)](#1-홈-페이지-pdf-업로드)
2. [분석 진행 상태 페이지](#2-분석-진행-상태-페이지)
3. [분석 결과 리포트 페이지](#3-분석-결과-리포트-페이지)
4. [분석 이력 페이지](#4-분석-이력-페이지)
5. [공통 컴포넌트](#5-공통-컴포넌트)
6. [API 연동 보완](#6-api-연동-보완)
7. [테스트 가이드](#7-테스트-가이드)

---

## 1. 홈 페이지 (PDF 업로드)

### 1.1 FileDropzone 컴포넌트

> 파일: `frontend/src/components/upload/FileDropzone.tsx`

```typescript
interface FileDropzoneProps {
  onFilesSelected: (files: File[]) => void;
  maxFiles?: number;
  maxSizeMB?: number;
}

// 구현 요점:
// - 드래그 앤 드롭 영역 (onDragOver, onDrop 이벤트)
// - 클릭 시 파일 선택 다이얼로그 (hidden input[type=file])
// - PDF만 허용 (accept=".pdf")
// - 드래그 오버 시 시각적 피드백 (border 색상 변경)
```

### 1.2 FileList 컴포넌트

> 파일: `frontend/src/components/upload/FileList.tsx`

```typescript
interface FileListProps {
  files: File[];
  onRemove: (index: number) => void;
}

// 구현 요점:
// - 파일명, 크기(MB) 표시
// - 삭제 버튼
// - 빈 상태 메시지
```

### 1.3 UploadForm 컴포넌트

> 파일: `frontend/src/components/upload/UploadForm.tsx`

```typescript
// 구현 요점:
// - 사건번호 (선택) 텍스트 입력
// - 메모 (선택) 텍스트 입력
// - "분석 시작" 버튼
// - 업로드 중 로딩 상태 + 진행률
// - 성공 시 AnalysisProgress 페이지로 이동 (useNavigate)
```

### 1.4 HomePage 조합

> 파일: `frontend/src/pages/HomePage.tsx`

```typescript
export function HomePage() {
  const [files, setFiles] = useState<File[]>([]);
  const navigate = useNavigate();
  const uploadMutation = useFileUpload();

  const handleSubmit = async (metadata: { description?: string; caseNumber?: string }) => {
    const result = await uploadMutation.mutateAsync({ files, ...metadata });
    navigate(`/analyses/${result.id}/status`);
  };

  return (
    <div>
      <h1>부동산 경매 분석 AI</h1>
      <FileDropzone onFilesSelected={(f) => setFiles([...files, ...f])} />
      <FileList files={files} onRemove={(i) => setFiles(files.filter((_, idx) => idx !== i))} />
      <UploadForm onSubmit={handleSubmit} isLoading={uploadMutation.isPending} />
    </div>
  );
}
```

---

## 2. 분석 진행 상태 페이지

### 2.1 ProgressTracker 컴포넌트

> 파일: `frontend/src/components/analysis/ProgressTracker.tsx`

```typescript
interface Stage {
  name: string;
  label: string;
  status: "pending" | "running" | "done" | "error";
  progress: number;
}

// 구현 요점:
// - 전체 진행률 바 (0~100%)
// - 6개 단계별 상태 표시
//   - pending: 회색 아이콘
//   - running: 파란색 스피너 + 진행률
//   - done: 초록색 체크
//   - error: 빨간색 X
// - 현재 작업 메시지 텍스트
```

### 2.2 WebSocket 연동

> 파일: `frontend/src/hooks/useWebSocket.ts` (기존 보완)

```typescript
export function useAnalysisProgress(analysisId: string) {
  const [progress, setProgress] = useState<AnalysisProgress | null>(null);
  const [isComplete, setIsComplete] = useState(false);

  useEffect(() => {
    const ws = new WebSocket(`ws://localhost:8000/ws/analyses/${analysisId}`);

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.type === "status_update") {
        setProgress(data);
      } else if (data.type === "analysis_complete") {
        setIsComplete(true);
      }
    };

    return () => ws.close();
  }, [analysisId]);

  return { progress, isComplete };
}
```

### 2.3 AnalysisProgressPage

> 파일: `frontend/src/pages/AnalysisProgressPage.tsx`

```typescript
// 구현 요점:
// - useParams()로 analysisId 가져오기
// - useAnalysisProgress(analysisId) 훅으로 실시간 상태
// - Polling 백업: useQuery로 5초마다 /status API 조회
// - 완료 시 "결과 보기" 버튼 → /analyses/{id}/report 이동
```

---

## 3. 분석 결과 리포트 페이지

### 3.1 RecommendationCard 컴포넌트

> 파일: `frontend/src/components/report/RecommendationCard.tsx`

```typescript
// 구현 요점:
// - 추천/보류/비추천 배지 (초록/노랑/빨강)
// - 추천 사유 텍스트
// - 신뢰도 점수 표시
```

### 3.2 PriceRangeCard 컴포넌트

> 파일: `frontend/src/components/report/PriceRangeCard.tsx`

```typescript
// 구현 요점:
// - 입찰 적정가: 보수적 / 적정 / 공격적 3단계
// - 매도 적정가: 비관적 / 기본 / 낙관적 3단계
// - 최저매각가격 표시
// - 금액 포맷팅 (억/만원 단위)
```

### 3.3 PriceChart 컴포넌트 (Recharts)

> 파일: `frontend/src/components/report/PriceChart.tsx`

```typescript
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";

// 구현 요점:
// - 월별 시세 변동 추이 차트
// - X축: 날짜 (월), Y축: 평균 거래가 (만원)
// - 감정가 기준선 표시
```

### 3.4 탭 컴포넌트 (권리분석/시세/뉴스/비용)

```typescript
// 4개 탭:
// - RightsAnalysisTab: 말소기준, 인수/소멸 권리 목록, 임차인 분석
// - MarketDataTab: 거래 이력 테이블, 시세 차트
// - NewsTab: 호재/악재 목록, 뉴스 요약
// - CostBreakdownTab: 비용 항목별 표, 수익률
```

### 3.5 면책 조항

```typescript
// DisclaimerBanner: 페이지 하단 경고 배너
// "본 분석 결과는 AI에 의한 참고용 정보이며, 최종 투자 판단의 책임은 사용자에게 있습니다."
```

### 3.6 ReportPage 조합

> 파일: `frontend/src/pages/ReportPage.tsx`

```typescript
export function ReportPage() {
  const { analysisId } = useParams();
  const { data: report, isLoading } = useQuery({
    queryKey: ["report", analysisId],
    queryFn: () => fetchReport(analysisId!),
  });

  if (isLoading) return <LoadingSkeleton />;
  if (!report) return <ErrorMessage />;

  return (
    <div>
      <RecommendationCard recommendation={report.recommendation} ... />
      <PriceRangeCard bidPrice={report.bid_price} salePrice={report.sale_price} />
      <PriceChart data={report.chart_data.price_trend} />
      <Tabs>
        <RightsAnalysisTab data={report.rights_analysis_summary} />
        <MarketDataTab data={report.market_summary} />
        <NewsTab data={report.news_summary} />
        <CostBreakdownTab data={report.cost_breakdown} profitability={report.profitability} />
      </Tabs>
      <DisclaimerBanner text={report.disclaimer} />
    </div>
  );
}
```

---

## 4. 분석 이력 페이지

> 파일: `frontend/src/pages/HistoryPage.tsx`

```typescript
// 구현 요점:
// - useAnalysisList() 훅으로 목록 조회
// - 카드 또는 테이블 형태 리스트
//   - 사건번호, 메모, 상태 배지, 생성일
// - 클릭 시:
//   - status=done → /analyses/{id}/report
//   - status=running → /analyses/{id}/status
// - 삭제 버튼 (확인 모달)
```

---

## 5. 공통 컴포넌트

### 5.1 Header

```typescript
// 네비게이션: 홈 / 분석 이력
// 로고 + 타이틀
```

### 5.2 Loading / ErrorBoundary

```typescript
// LoadingSkeleton: 스켈레톤 UI
// ErrorBoundary: React ErrorBoundary + 에러 메시지
```

---

## 6. API 연동 보완

### 6.1 API 함수 추가

> 파일: `frontend/src/api/client.ts`

```typescript
export async function createAnalysis(files: File[], metadata?: { description?: string; caseNumber?: string }) {
  const formData = new FormData();
  files.forEach((f) => formData.append("files", f));
  if (metadata?.description) formData.append("description", metadata.description);
  if (metadata?.caseNumber) formData.append("case_number", metadata.caseNumber);

  const { data } = await api.post("/analyses", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return data;
}

export async function fetchAnalysisStatus(id: string) {
  const { data } = await api.get(`/analyses/${id}/status`);
  return data;
}

export async function fetchReport(id: string) {
  const { data } = await api.get(`/analyses/${id}/report`);
  return data;
}
```

---

## 7. 테스트 가이드

### 7.1 테스트 케이스

| ID | 테스트명 | 설명 | 기대 결과 |
|:---:|:---|:---|:---|
| T-1 | 파일 업로드 + 분석 시작 | 홈에서 PDF 업로드 → 분석 시작 | 진행 상태 페이지 이동 |
| T-2 | 비 PDF 파일 거부 | txt 파일 드래그 | 에러 메시지 |
| T-3 | 진행률 실시간 표시 | WebSocket 수신 | 단계별 상태 업데이트 |
| T-4 | 리포트 정상 표시 | 완료된 분석 조회 | 추천/가격/차트 표시 |
| T-5 | 이력 목록 조회 | 이력 페이지 접근 | 분석 카드 리스트 |

### 7.2 수동 테스트 체크리스트

```
[ ] 홈 페이지: PDF 드래그 앤 드롭 동작
[ ] 홈 페이지: 파일 삭제 버튼 동작
[ ] 홈 페이지: 분석 시작 버튼 → 로딩 → 이동
[ ] 진행 상태: 단계별 상태 변화 확인
[ ] 진행 상태: 완료 시 "결과 보기" 버튼 표시
[ ] 리포트: 추천 카드 색상 확인
[ ] 리포트: 시세 차트 렌더링
[ ] 리포트: 탭 전환 동작
[ ] 리포트: 면책 조항 표시
[ ] 이력: 목록 표시 및 클릭 이동
[ ] 모바일 반응형 확인 (360px)
```

---

## 파일 변경 요약

### 수정 파일

| 파일 경로 | 변경 내용 |
|:---|:---|
| `frontend/src/pages/HomePage.tsx` | 업로드 폼 + 파일 목록 완성 |
| `frontend/src/pages/AnalysisProgressPage.tsx` | WebSocket + 진행률 UI |
| `frontend/src/pages/ReportPage.tsx` | 리포트 대시보드 전체 |
| `frontend/src/pages/HistoryPage.tsx` | 이력 리스트 |
| `frontend/src/hooks/useWebSocket.ts` | 실시간 진행률 훅 보완 |
| `frontend/src/api/client.ts` | API 함수 추가 |

### 신규 생성 파일

| 파일 경로 | 설명 |
|:---|:---|
| `frontend/src/components/upload/FileDropzone.tsx` | 드래그 앤 드롭 |
| `frontend/src/components/upload/FileList.tsx` | 파일 목록 |
| `frontend/src/components/upload/UploadForm.tsx` | 업로드 폼 |
| `frontend/src/components/analysis/ProgressTracker.tsx` | 진행률 표시 |
| `frontend/src/components/report/RecommendationCard.tsx` | 추천 카드 |
| `frontend/src/components/report/PriceRangeCard.tsx` | 가격 범위 카드 |
| `frontend/src/components/report/PriceChart.tsx` | 시세 차트 |
| `frontend/src/components/report/RightsAnalysisTab.tsx` | 권리분석 탭 |
| `frontend/src/components/report/MarketDataTab.tsx` | 시세분석 탭 |
| `frontend/src/components/report/NewsTab.tsx` | 뉴스 탭 |
| `frontend/src/components/report/CostBreakdownTab.tsx` | 비용 탭 |
| `frontend/src/components/report/DisclaimerBanner.tsx` | 면책 배너 |
| `frontend/src/components/common/Header.tsx` | 헤더 |
| `frontend/src/components/common/Loading.tsx` | 로딩 스켈레톤 |
