# Task-04: 뉴스 분석 에이전트 구현

> **참조 스펙**: PRD-04 전체
> **예상 작업 시간**: 4~6시간
> **선행 작업**: Task-01 (문서 파싱 - 소재지 정보 필요)
> **변경 파일 수**: 3~4개

---

## 목차

1. [네이버 뉴스 API 클라이언트](#1-네이버-뉴스-api-클라이언트)
2. [뉴스 분류 및 요약 (Claude)](#2-뉴스-분류-및-요약-claude)
3. [에이전트 노드 구현](#3-에이전트-노드-구현)
4. [테스트 가이드](#4-테스트-가이드)

---

## 1. 네이버 뉴스 API 클라이언트

### 1.1 뉴스 검색 구현

> 파일: `backend/app/agents/tools/news_api.py`

```python
import httpx
from app.config import settings

NAVER_SEARCH_URL = "https://openapi.naver.com/v1/search/news.json"

async def search_news(
    query: str,
    display: int = 20,
    sort: str = "date",
) -> list[dict]:
    """
    네이버 뉴스 검색 API 호출

    Args:
        query: 검색 키워드 (예: "강남구 역삼동 재개발")
        display: 검색 결과 수 (최대 100)
        sort: 정렬 방식 (date: 날짜순, sim: 관련도순)
    """
    headers = {
        "X-Naver-Client-Id": settings.NAVER_CLIENT_ID,
        "X-Naver-Client-Secret": settings.NAVER_CLIENT_SECRET,
    }
    params = {
        "query": query,
        "display": display,
        "sort": sort,
    }

    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(NAVER_SEARCH_URL, headers=headers, params=params)
        response.raise_for_status()

    data = response.json()
    return data.get("items", [])
```

### 1.2 검색 키워드 자동 생성

```python
def generate_search_queries(address: str) -> list[str]:
    """
    소재지 주소에서 검색 키워드 생성

    예: "서울시 강남구 역삼동" →
      - "강남구 역삼동 부동산"
      - "강남구 재개발"
      - "강남구 개발 호재"
      - "역삼동 교통"
      - "강남구 부동산 시장"
    """
    # 주소에서 구/동 추출
    parts = address.split()
    gu = next((p for p in parts if p.endswith("구")), "")
    dong = next((p for p in parts if p.endswith("동")), "")

    queries = []
    if gu:
        queries.extend([
            f"{gu} 부동산 시장",
            f"{gu} 재개발 재건축",
            f"{gu} 개발 호재",
            f"{gu} 부동산 전망",
        ])
    if dong:
        queries.extend([
            f"{dong} 부동산",
            f"{dong} 개발",
        ])
    return queries
```

---

## 2. 뉴스 분류 및 요약 (Claude)

### 2.1 뉴스 분석 프롬프트

```python
NEWS_ANALYSIS_PROMPT = """
다음 뉴스 목록을 분석하여 부동산 투자 관점에서 평가해주세요.
대상 지역: {area}

각 뉴스에 대해:
1. sentiment: "호재" | "악재" | "중립"
2. impact_score: 0~10 (부동산 가치 영향도)
3. category: "개발" | "교통" | "교육" | "생활인프라" | "정책" | "시장동향"
4. summary: 핵심 내용 1~2문장 요약

종합 분석:
- positive_factors: 호재 요소 목록 (title, description, impact_level, timeline)
- negative_factors: 악재 요소 목록
- area_attractiveness_score: 0~100 (지역 매력도)
- investment_opinion: 투자 관점 종합 의견 (3~5문장)
- outlook: "긍정" | "중립" | "부정"

뉴스 목록:
{news_list}

JSON으로 응답해주세요.
"""
```

### 2.2 뉴스 분석 함수

```python
from anthropic import Anthropic

async def analyze_news_with_claude(
    news_items: list[dict],
    target_area: str,
) -> dict:
    """Claude를 활용한 뉴스 분류/요약/종합 분석"""
    # 뉴스 포맷팅
    news_text = "\n".join(
        f"- 제목: {n['title']}\n  내용: {n.get('description', '')}\n  날짜: {n.get('pubDate', '')}"
        for n in news_items
    )

    client = Anthropic()
    response = client.messages.create(
        model="claude-sonnet-4-5-20250929",
        max_tokens=4000,
        messages=[{
            "role": "user",
            "content": NEWS_ANALYSIS_PROMPT.format(area=target_area, news_list=news_text),
        }],
    )
    # JSON 파싱 후 반환
```

---

## 3. 에이전트 노드 구현

### 3.1 news_analysis 노드

> 파일: `backend/app/agents/nodes/news_analysis.py`

```python
async def news_analysis_node(state: AgentState) -> AgentState:
    """
    처리 흐름:
    1. state에서 소재지 정보 가져오기
    2. 검색 키워드 자동 생성
    3. 키워드별 네이버 뉴스 API 호출
    4. 중복 뉴스 제거
    5. Claude로 뉴스 분류/요약/종합 분석
    6. NewsAnalysisResult 생성
    """
    registry = state.get("registry")
    if not registry:
        return {**state, "news_analysis": None, "errors": state.get("errors", []) + ["소재지 정보 없음"]}

    address = registry.property_address
    queries = generate_search_queries(address)

    # 뉴스 수집
    all_news = []
    seen_titles = set()
    for query in queries:
        try:
            items = await search_news(query, display=10)
            for item in items:
                title = item.get("title", "")
                if title not in seen_titles:
                    seen_titles.add(title)
                    all_news.append(item)
        except Exception:
            continue

    if not all_news:
        return {**state, "news_analysis": None, "errors": state.get("errors", []) + ["뉴스 수집 실패"]}

    # Claude 분석 (최대 50건)
    analysis = await analyze_news_with_claude(all_news[:50], address)

    result = NewsAnalysisResult(
        target_area=address,
        collected_news=analysis["analyzed_news"],
        positive_factors=analysis["positive_factors"],
        negative_factors=analysis["negative_factors"],
        area_attractiveness_score=analysis["area_attractiveness_score"],
        investment_opinion=analysis["investment_opinion"],
        outlook=analysis["outlook"],
        confidence_score=analysis.get("confidence", 0.7),
    )

    return {**state, "news_analysis": result}
```

---

## 4. 테스트 가이드

### 4.1 테스트 케이스

| ID | 테스트명 | 설명 | 기대 결과 |
|:---:|:---|:---|:---|
| T-1 | `test_generate_queries` | 주소 → 키워드 생성 | 5개 이상 키워드 |
| T-2 | `test_search_news_api` | 네이버 API 호출 (mock) | 뉴스 리스트 반환 |
| T-3 | `test_dedup_news` | 중복 뉴스 제거 | 고유 제목만 유지 |
| T-4 | `test_analyze_news_claude` | Claude 분석 (mock) | 호재/악재 분류 |
| T-5 | `test_news_node_no_address` | 주소 없음 | 에러 메시지 |

### 4.2 테스트 실행

```bash
cd backend
uv run pytest tests/unit/agents/test_news_analysis.py -v
```

---

## 파일 변경 요약

### 수정 파일

| 파일 경로 | 변경 내용 |
|:---|:---|
| `backend/app/agents/tools/news_api.py` | 네이버 뉴스 API 클라이언트 구현 |
| `backend/app/agents/nodes/news_analysis.py` | 뉴스 분석 노드 구현 |

### 신규 생성 파일

| 파일 경로 | 설명 |
|:---|:---|
| `backend/app/agents/prompts/news_prompts.py` | 뉴스 분석 LLM 프롬프트 |
| `backend/tests/unit/agents/test_news_analysis.py` | 단위 테스트 |
