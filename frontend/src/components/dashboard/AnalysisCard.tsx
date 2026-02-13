import { useNavigate } from 'react-router-dom'
import type { Analysis, Recommendation, AnalysisStatus } from '../../types'

const RECOMMENDATION_BADGE: Record<Recommendation, { label: string; className: string }> = {
  recommend: { label: '추천', className: 'bg-green-100 text-green-800' },
  hold: { label: '보류', className: 'bg-yellow-100 text-yellow-800' },
  not_recommend: { label: '비추천', className: 'bg-red-100 text-red-800' },
}

const STATUS_BADGE: Record<Exclude<AnalysisStatus, 'done'>, { label: string; className: string }> = {
  pending: { label: '대기중', className: 'bg-gray-100 text-gray-600' },
  running: { label: '분석중', className: 'bg-blue-100 text-blue-700' },
  error: { label: '오류', className: 'bg-red-100 text-red-700' },
}

function formatKRW(value: number): string {
  if (value >= 100_000_000) {
    const eok = Math.floor(value / 100_000_000)
    const man = Math.floor((value % 100_000_000) / 10_000)
    return man > 0 ? `${eok}억 ${man.toLocaleString()}만원` : `${eok}억원`
  }
  if (value >= 10_000) {
    return `${Math.floor(value / 10_000).toLocaleString()}만원`
  }
  return `${value.toLocaleString()}원`
}

interface AnalysisCardProps {
  analysis: Analysis
  onToggleFavorite: (id: string) => void
  onDelete: (id: string) => void
  isDeleteConfirm: boolean
}

export default function AnalysisCard({ analysis, onToggleFavorite, onDelete, isDeleteConfirm }: AnalysisCardProps) {
  const navigate = useNavigate()

  const handleClick = () => {
    if (analysis.status === 'done') {
      navigate(`/report/${analysis.id}`)
    } else {
      navigate(`/analysis/${analysis.id}`)
    }
  }

  const handleFavoriteClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    onToggleFavorite(analysis.id)
  }

  const handleDeleteClick = (e: React.MouseEvent) => {
    e.stopPropagation()
    onDelete(analysis.id)
  }

  const displayName = analysis.property_name || analysis.property_address || '--'
  const propertyInfo = [analysis.property_type, analysis.area != null ? `${analysis.area}㎡` : null]
    .filter(Boolean)
    .join(' | ')

  return (
    <div
      onClick={handleClick}
      className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-md hover:border-gray-300 transition-all cursor-pointer"
    >
      {/* Top row: recommendation badge + favorite star */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          {analysis.recommendation && (
            <span
              className={`px-2.5 py-0.5 rounded-full text-xs font-bold ${RECOMMENDATION_BADGE[analysis.recommendation].className}`}
            >
              {RECOMMENDATION_BADGE[analysis.recommendation].label}
            </span>
          )}
          {analysis.status !== 'done' && (
            <span
              className={`px-2.5 py-0.5 rounded-full text-xs font-medium ${STATUS_BADGE[analysis.status].className}`}
            >
              {STATUS_BADGE[analysis.status].label}
            </span>
          )}
        </div>
        <div className="flex items-center gap-1">
          <button
            onClick={handleFavoriteClick}
            className="p-1 rounded-full hover:bg-gray-100 transition-colors"
            aria-label={analysis.is_favorite ? '즐겨찾기 해제' : '즐겨찾기 추가'}
          >
            {analysis.is_favorite ? (
              <svg className="w-5 h-5 text-yellow-400" fill="currentColor" viewBox="0 0 20 20">
                <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
              </svg>
            ) : (
              <svg className="w-5 h-5 text-gray-300 hover:text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M11.48 3.499a.562.562 0 011.04 0l2.125 5.111a.563.563 0 00.475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 00-.182.557l1.285 5.385a.562.562 0 01-.84.61l-4.725-2.885a.563.563 0 00-.586 0L6.982 20.54a.562.562 0 01-.84-.61l1.285-5.386a.562.562 0 00-.182-.557l-4.204-3.602a.563.563 0 01.321-.988l5.518-.442a.563.563 0 00.475-.345L11.48 3.5z" />
              </svg>
            )}
          </button>
          <button
            onClick={handleDeleteClick}
            className={`p-1 rounded-full transition-colors ${
              isDeleteConfirm
                ? 'text-red-500 bg-red-50 hover:bg-red-100'
                : 'text-gray-300 hover:text-red-500 hover:bg-gray-100'
            }`}
            aria-label="삭제"
            title={isDeleteConfirm ? '한 번 더 클릭하면 삭제됩니다' : '삭제'}
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052.682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4.772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12 .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 013.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51.964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.201v.916m7.5 0a48.667 48.667 0 00-7.5 0" />
            </svg>
          </button>
        </div>
      </div>

      {/* Case number */}
      {analysis.case_number && (
        <p className="text-xs text-gray-400 mb-1">{analysis.case_number}</p>
      )}

      {/* Property name / address */}
      <h3 className="text-sm font-semibold text-gray-900 mb-1 line-clamp-2">{displayName}</h3>

      {/* Property type + area */}
      {propertyInfo && (
        <p className="text-xs text-gray-500 mb-3">{propertyInfo}</p>
      )}

      {/* Appraised value */}
      {analysis.appraised_value != null && (
        <div className="mb-2">
          <span className="text-xs text-gray-400">감정가</span>
          <p className="text-base font-bold text-gray-900">{formatKRW(analysis.appraised_value)}</p>
        </div>
      )}

      {/* Expected ROI */}
      {analysis.expected_roi != null && (
        <div className="mb-3">
          <span className="text-xs text-gray-400">예상 수익률</span>
          <p
            className={`text-sm font-semibold ${
              analysis.expected_roi >= 0 ? 'text-green-600' : 'text-red-600'
            }`}
          >
            {analysis.expected_roi >= 0 ? '+' : ''}
            {analysis.expected_roi.toFixed(1)}%
          </p>
        </div>
      )}

      {/* Date */}
      <p className="text-xs text-gray-400 mt-auto pt-2 border-t border-gray-100">
        {new Date(analysis.created_at).toLocaleDateString('ko-KR')}
      </p>
    </div>
  )
}
