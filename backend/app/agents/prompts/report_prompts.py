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
1. property_overview: 물건 개요 - 물건 종류(아파트/다세대/다가구/오피스텔 등), 소재지, 면적, 감정가 등 핵심 정보 (2~3문장)
2. rights_summary: 권리분석 핵심 요약 - 말소기준권리, 인수할 권리 유무, 임차인 대항력 여부, 위험도 판단 (3~5문장)
3. market_summary: 시세 분석 요약 - 실거래 시세, 감정가 대비 시세 수준, 가격 추이(상승/보합/하락) (3~5문장)
4. news_summary: 뉴스/동향 요약 - 해당 지역의 호재/악재, 개발 계획, 부동산 시장 전망 (3~5문장)
5. bid_price_reasoning: 입찰 적정가 산출 근거 - 왜 이 가격대를 추천하는지 추정시세, 부대비용, 인수비용 등을 근거로 설명 (3~5문장)
6. sale_price_reasoning: 매도 적정가 산출 근거 - 왜 이 가격에 매도할 수 있는지 시세추이, 호재/악재 등을 근거로 설명 (3~5문장)
7. overall_opinion: 종합 의견 (5~7문장)

반드시 아래 JSON 형식으로만 응답해주세요 (다른 텍스트 없이):
{{"property_overview": "...", "rights_summary": "...", "market_summary": "...", "news_summary": "...", "bid_price_reasoning": "...", "sale_price_reasoning": "...", "overall_opinion": "..."}}
"""
