import { Link, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { fetchAnalysisStatus } from '../api/client'
import { useWebSocket } from '../hooks/useWebSocket'
import ProgressTracker from '../components/analysis/ProgressTracker'
import { Spinner } from '../components/common/Loading'

export default function AnalysisProgress() {
  const { id } = useParams<{ id: string }>()
  const { progress, isComplete } = useWebSocket(id)

  // Polling 백업: 5초마다 상태 조회
  const { data: polledStatus } = useQuery({
    queryKey: ['analysis-status', id],
    queryFn: () => fetchAnalysisStatus(id!),
    enabled: !!id && !isComplete,
    refetchInterval: 5000,
  })

  // WebSocket이 없으면 polling 데이터 사용
  // polling 응답은 { id, status, progress: { overall, stages } } 구조
  const currentProgress = progress ?? polledStatus?.progress

  // 완료 시 자동 이동하지 않고 버튼 표시
  const isDone = isComplete || polledStatus?.status === 'done'

  return (
    <div className="max-w-2xl mx-auto py-8 px-4">
      <h1 className="text-2xl font-bold text-gray-900 mb-2">분석 진행 현황</h1>
      <p className="text-sm text-gray-400 mb-8">분석 ID: {id}</p>

      <div className="bg-white rounded-xl border border-gray-200 p-6">
        {currentProgress ? (
          <ProgressTracker
            overall={currentProgress.overall ?? 0}
            stages={currentProgress.stages ?? {}}
          />
        ) : (
          <div className="flex items-center justify-center gap-3 py-12">
            <Spinner />
            <span className="text-sm text-gray-500">분석을 준비하고 있습니다...</span>
          </div>
        )}
      </div>

      {isDone && (
        <div className="mt-6 text-center">
          <Link
            to={`/report/${id}`}
            className="inline-flex items-center gap-2 px-6 py-3 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 transition-colors"
          >
            결과 보기
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
            </svg>
          </Link>
        </div>
      )}
    </div>
  )
}
