import type { StageProgress } from '../../types'

interface Stage {
  key: string
  label: string
  progress: StageProgress
}

const STAGE_LABELS: Record<string, string> = {
  parsed_documents: '문서 파싱',
  rights_analysis: '권리 분석',
  market_data: '시세 분석',
  news_analysis: '뉴스 분석',
  valuation: '가치 평가',
  report: '보고서 생성',
}

function StageIcon({ status }: { status: StageProgress['status'] }) {
  switch (status) {
    case 'done':
      return (
        <div className="w-8 h-8 rounded-full bg-green-100 flex items-center justify-center">
          <svg className="w-5 h-5 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>
      )
    case 'running':
      return (
        <div className="w-8 h-8 rounded-full bg-blue-100 flex items-center justify-center">
          <svg className="w-5 h-5 text-blue-600 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
        </div>
      )
    case 'error':
      return (
        <div className="w-8 h-8 rounded-full bg-red-100 flex items-center justify-center">
          <svg className="w-5 h-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </div>
      )
    default:
      return <div className="w-8 h-8 rounded-full bg-gray-200" />
  }
}

interface ProgressTrackerProps {
  overall: number
  stages: Record<string, StageProgress>
}

export default function ProgressTracker({ overall, stages }: ProgressTrackerProps) {
  const stageList: Stage[] = Object.entries(STAGE_LABELS).map(([key, label]) => ({
    key,
    label,
    progress: stages[key] ?? { status: 'pending', progress: 0 },
  }))

  return (
    <div className="space-y-6">
      {/* 전체 진행률 */}
      <div>
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-700">전체 진행률</span>
          <span className="text-sm font-bold text-blue-600">{overall}%</span>
        </div>
        <div className="w-full bg-gray-200 rounded-full h-3">
          <div
            className="bg-blue-600 h-3 rounded-full transition-all duration-500"
            style={{ width: `${Math.min(overall, 100)}%` }}
          />
        </div>
      </div>

      {/* 단계별 상태 */}
      <div className="space-y-3">
        {stageList.map(({ key, label, progress }) => (
          <div key={key} className="flex items-center gap-4">
            <StageIcon status={progress.status} />
            <div className="flex-1 min-w-0">
              <div className="flex items-center justify-between">
                <span
                  className={`text-sm font-medium ${
                    progress.status === 'running'
                      ? 'text-blue-700'
                      : progress.status === 'done'
                        ? 'text-green-700'
                        : progress.status === 'error'
                          ? 'text-red-700'
                          : 'text-gray-500'
                  }`}
                >
                  {label}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
