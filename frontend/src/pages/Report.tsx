import { useState, useMemo } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { fetchReport } from '../api/client'
import type { AnalysisDetail, AnalysisReport } from '../types'
import { LoadingSkeleton, ErrorMessage } from '../components/common/Loading'
import PropertyInfoCard from '../components/report/PropertyInfoCard'
import RecommendationCard from '../components/report/RecommendationCard'
import PriceRangeCard from '../components/report/PriceRangeCard'
import PriceChart from '../components/report/PriceChart'
import RightsAnalysisTab from '../components/report/RightsAnalysisTab'
import MarketDataTab from '../components/report/MarketDataTab'
import NewsTab from '../components/report/NewsTab'
import CostBreakdownTab from '../components/report/CostBreakdownTab'
import DisclaimerBanner from '../components/report/DisclaimerBanner'

const TABS = [
  { key: 'rights', label: '권리분석' },
  { key: 'market', label: '시세분석' },
  { key: 'news', label: '뉴스' },
  { key: 'cost', label: '비용/수익' },
] as const

type TabKey = (typeof TABS)[number]['key']

/** chart_data.price_trend가 유효한지 (날짜가 비어있지 않은지) 확인 */
function hasValidDates(data: { date: string; price: number }[]): boolean {
  return data.length > 0 && data[0].date.length >= 7
}

/** market_data.recent_transactions에서 월별 평균을 재구성 */
function buildMonthlyFromTransactions(
  marketData: Record<string, unknown> | null,
): { date: string; price: number }[] {
  if (!marketData) return []
  const txns = marketData.recent_transactions as
    | { transaction_date: string; price: number }[]
    | undefined
  if (!txns?.length) return []

  const monthly: Record<string, { sum: number; count: number }> = {}
  for (const t of txns) {
    if (!t.transaction_date || t.transaction_date.length < 7) continue
    const key = t.transaction_date.substring(0, 7)
    if (!monthly[key]) monthly[key] = { sum: 0, count: 0 }
    monthly[key].sum += t.price
    monthly[key].count++
  }
  return Object.entries(monthly)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([date, { sum, count }]) => ({ date, price: Math.round(sum / count) }))
}

/** 차트 데이터 구성: price_trend 우선, fallback으로 market_data에서 재구성 */
function buildChartData(
  report: AnalysisReport | null,
  marketData: Record<string, unknown> | null,
): { date: string; price: number }[] {
  const priceTrend = report?.chart_data?.price_trend ?? []
  if (hasValidDates(priceTrend)) return priceTrend
  return buildMonthlyFromTransactions(marketData)
}

/** parsed_documents에서 사건번호/채무자/채권자 추출 */
function extractParsedInfo(detail: AnalysisDetail) {
  const parsed = detail.parsed_documents as Record<string, Record<string, unknown>> | null
  const registry = parsed?.registry as
    | { owner?: string; section_b_entries?: { holder: string; right_type: string }[] }
    | undefined
  const saleItem = parsed?.sale_item as { case_number?: string } | undefined
  return {
    caseNumber: detail.case_number || saleItem?.case_number || null,
    debtorName: registry?.owner ?? null,
    creditorName: registry?.section_b_entries?.[0]?.holder ?? null,
  }
}

export default function Report() {
  const { id } = useParams<{ id: string }>()
  const [activeTab, setActiveTab] = useState<TabKey>('rights')

  const { data: detail, isLoading, error } = useQuery({
    queryKey: ['report', id],
    queryFn: () => fetchReport(id!),
    enabled: !!id,
  })

  // 모든 Hook은 early return 앞에 위치해야 함
  const chartData = useMemo(
    () => buildChartData(detail?.report ?? null, (detail?.market_data as Record<string, unknown>) ?? null),
    [detail?.report, detail?.market_data],
  )

  const { caseNumber, debtorName, creditorName } = useMemo(
    () => (detail ? extractParsedInfo(detail) : { caseNumber: null, debtorName: null, creditorName: null }),
    [detail],
  )

  if (isLoading) return <LoadingSkeleton />
  if (error || !detail) return <ErrorMessage message="리포트를 불러올 수 없습니다." />

  const report = detail.report

  if (!report) return <ErrorMessage message="분석이 아직 완료되지 않았습니다." />

  if ('error' in report && !report.recommendation) {
    return <ErrorMessage message={`분석 중 오류가 발생했습니다: ${report.error}`} />
  }

  // analysis_summary에서 전체 의견 추출 (partial report 대비)
  const summary = (report as unknown as Record<string, unknown>).analysis_summary as Record<string, string> | undefined
  const hasValuation = !!report.recommendation

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">분석 리포트</h1>

      {/* 물건 정보 */}
      <PropertyInfoCard
        caseNumber={caseNumber}
        address={detail.property_address}
        propertyType={detail.property_type}
        debtorName={debtorName}
        creditorName={creditorName}
      />

      {/* 추천 카드 + 가격 분석 */}
      {hasValuation ? (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <RecommendationCard
            recommendation={report.recommendation}
            reasoning={report.reasoning}
            confidenceScore={report.confidence_score}
          />
          <PriceRangeCard bidPrice={report.bid_price} salePrice={report.sale_price} />
        </div>
      ) : (
        <div className="bg-yellow-50 border border-yellow-200 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-yellow-800 mb-2">부분 분석 완료</h3>
          <p className="text-sm text-yellow-700">
            {summary?.overall_opinion
              ?? '일부 분석 데이터가 부족합니다. 등기부등본, 감정평가서 등을 추가로 업로드하면 전체 분석을 받을 수 있습니다.'}
          </p>
        </div>
      )}

      {/* 시세 차트 */}
      <PriceChart data={chartData} />

      {/* 탭 영역 */}
      <div className="bg-white rounded-xl border border-gray-200">
        <div className="border-b border-gray-200">
          <nav className="flex -mb-px">
            {TABS.map(({ key, label }) => (
              <button
                key={key}
                onClick={() => setActiveTab(key)}
                className={`px-6 py-3 text-sm font-medium border-b-2 transition-colors ${
                  activeTab === key
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                {label}
              </button>
            ))}
          </nav>
        </div>
        <div className="p-6">
          {activeTab === 'rights' && (
            <RightsAnalysisTab data={detail.rights_analysis as Record<string, unknown> | undefined} />
          )}
          {activeTab === 'market' && (
            <MarketDataTab data={detail.market_data as Record<string, unknown> | undefined} />
          )}
          {activeTab === 'news' && (
            <NewsTab data={detail.news_analysis as Record<string, unknown> | undefined} />
          )}
          {activeTab === 'cost' && (
            <CostBreakdownTab data={report.cost_breakdown} expectedRoi={report.expected_roi} />
          )}
        </div>
      </div>

      {/* 면책 배너 */}
      <DisclaimerBanner text={report.disclaimer} />
    </div>
  )
}
