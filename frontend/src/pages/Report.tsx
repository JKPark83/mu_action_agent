import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { fetchReport } from '../api/client'
import { LoadingSkeleton, ErrorMessage } from '../components/common/Loading'
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

export default function Report() {
  const { id } = useParams<{ id: string }>()
  const [activeTab, setActiveTab] = useState<TabKey>('rights')

  const { data: detail, isLoading, error } = useQuery({
    queryKey: ['report', id],
    queryFn: () => fetchReport(id!),
    enabled: !!id,
  })

  if (isLoading) return <LoadingSkeleton />
  if (error || !detail) return <ErrorMessage message="리포트를 불러올 수 없습니다." />

  const report = detail.report

  if (!report) return <ErrorMessage message="분석이 아직 완료되지 않았습니다." />

  if ('error' in report && !report.recommendation) {
    return <ErrorMessage message={`분석 중 오류가 발생했습니다: ${report.error}`} />
  }

  // analysis_summary에서 전체 의견 추출 (partial report 대비)
  const summary = (report as Record<string, unknown>).analysis_summary as Record<string, string> | undefined
  const hasValuation = !!report.recommendation

  return (
    <div className="max-w-4xl mx-auto py-8 px-4 space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">분석 리포트</h1>

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
      <PriceChart data={report.chart_data?.price_trend ?? []} />

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
