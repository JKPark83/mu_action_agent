"""보고서 생성 LLM 프롬프트 템플릿"""

REPORT_PROMPT = """\
다음 경매 분석 결과를 기반으로 최종 분석 리포트를 생성해주세요.
비전문가도 쉽게 이해할 수 있는 용어를 사용하세요.

## 권리분석 결과
{rights}

## 시장 데이터
{market}

## 뉴스 분석
{news}

## 가치 평가
{valuation}

리포트 구조:
1. property_overview: 물건 개요 (2~3문장)
2. rights_summary: 권리분석 핵심 요약 (3~5문장)
3. market_summary: 시세 분석 요약 (3~5문장)
4. news_summary: 뉴스/동향 요약 (3~5문장)
5. overall_opinion: 종합 의견 (5~7문장)

반드시 아래 JSON 형식으로만 응답해주세요 (다른 텍스트 없이):
{{"property_overview": "...", "rights_summary": "...", "market_summary": "...", "news_summary": "...", "overall_opinion": "..."}}
"""
