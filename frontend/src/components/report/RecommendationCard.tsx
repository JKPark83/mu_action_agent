import type { Recommendation } from '../../types'

const BADGE_CONFIG: Record<Recommendation, { label: string; bg: string; text: string }> = {
  recommend: { label: '추천', bg: 'bg-green-100', text: 'text-green-800' },
  hold: { label: '보류', bg: 'bg-yellow-100', text: 'text-yellow-800' },
  not_recommend: { label: '비추천', bg: 'bg-red-100', text: 'text-red-800' },
}

interface RecommendationCardProps {
  recommendation: Recommendation
  reasoning: string
  confidenceScore?: number
}

export default function RecommendationCard({ recommendation, reasoning, confidenceScore }: RecommendationCardProps) {
  const badge = BADGE_CONFIG[recommendation]

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">투자 추천</h3>
        <span className={`px-3 py-1 rounded-full text-sm font-bold ${badge.bg} ${badge.text}`}>{badge.label}</span>
      </div>
      <p className="text-gray-600 text-sm leading-relaxed">{reasoning}</p>
      {confidenceScore != null && (
        <div className="mt-4 flex items-center gap-2">
          <span className="text-xs text-gray-400">신뢰도</span>
          <div className="flex-1 bg-gray-100 rounded-full h-2">
            <div
              className="bg-blue-500 h-2 rounded-full"
              style={{ width: `${Math.round(confidenceScore * 100)}%` }}
            />
          </div>
          <span className="text-xs font-medium text-gray-600">{Math.round(confidenceScore * 100)}%</span>
        </div>
      )}
    </div>
  )
}
