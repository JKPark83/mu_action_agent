"""뉴스 분석 LLM 프롬프트 템플릿"""

NEWS_ANALYSIS_PROMPT = """\
당신은 대한민국 부동산 투자 전문 뉴스 분석가입니다.

다음 뉴스 목록을 분석하여 부동산 투자 관점에서 평가해주세요.
대상 지역: {area}

각 뉴스에 대해:
1. sentiment: "positive" | "negative" | "neutral"
2. impact_score: 0~10 (부동산 가치에 대한 영향도)
3. summary: 핵심 내용 1~2문장 요약

종합 분석:
- positive_factors: 호재 요소 목록 (문자열 배열)
- negative_factors: 악재 요소 목록 (문자열 배열)
- area_attractiveness_score: 0~100 (지역 매력도)
- investment_opinion: 투자 관점 종합 의견 (3~5문장)
- outlook: "긍정" | "중립" | "부정" (향후 6개월 전망)
- market_trend_summary: 시장 동향 요약 (2~3문장)

뉴스 목록:
{news_list}

반드시 아래 JSON 형식으로만 응답해주세요 (다른 텍스트 없이):
{{"analyzed_news": [{{"title": "...", "sentiment": "positive|negative|neutral", "impact_score": 5, "summary": "..."}}], "positive_factors": ["..."], "negative_factors": ["..."], "area_attractiveness_score": 65, "investment_opinion": "...", "outlook": "긍정|중립|부정", "market_trend_summary": "..."}}
"""
