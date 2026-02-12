import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useAnalysisList } from '../hooks/useAnalysis'
import { deleteAnalysis } from '../api/client'
import { LoadingSkeleton, ErrorMessage } from '../components/common/Loading'
import type { Analysis } from '../types'

const STATUS_BADGE: Record<string, { label: string; className: string }> = {
  pending: { label: '대기중', className: 'bg-gray-100 text-gray-600' },
  running: { label: '분석중', className: 'bg-blue-100 text-blue-700' },
  done: { label: '완료', className: 'bg-green-100 text-green-700' },
  error: { label: '오류', className: 'bg-red-100 text-red-700' },
}

function AnalysisCard({ analysis, onDelete }: { analysis: Analysis; onDelete: (id: string) => void }) {
  const badge = STATUS_BADGE[analysis.status] ?? STATUS_BADGE.pending
  const linkTo = analysis.status === 'done' ? `/report/${analysis.id}` : `/analysis/${analysis.id}`

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-sm transition-shadow">
      <div className="flex items-start justify-between">
        <Link to={linkTo} className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-2">
            <span className={`px-2 py-0.5 rounded text-xs font-medium ${badge.className}`}>{badge.label}</span>
            {analysis.case_number && (
              <span className="text-sm font-medium text-gray-700">{analysis.case_number}</span>
            )}
          </div>
          {analysis.description && (
            <p className="text-sm text-gray-600 truncate mb-2">{analysis.description}</p>
          )}
          <p className="text-xs text-gray-400">
            {new Date(analysis.created_at).toLocaleDateString('ko-KR', {
              year: 'numeric',
              month: 'long',
              day: 'numeric',
              hour: '2-digit',
              minute: '2-digit',
            })}
          </p>
        </Link>
        <button
          onClick={(e) => {
            e.preventDefault()
            onDelete(analysis.id)
          }}
          className="text-gray-300 hover:text-red-500 transition-colors p-1 ml-2"
          aria-label="삭제"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
            />
          </svg>
        </button>
      </div>
    </div>
  )
}

export default function History() {
  const { data: analyses, isLoading, error, refetch } = useAnalysisList()
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)

  const handleDelete = async (id: string) => {
    if (deleteConfirm === id) {
      await deleteAnalysis(id)
      setDeleteConfirm(null)
      refetch()
    } else {
      setDeleteConfirm(id)
      // 3초 후 확인 상태 리셋
      setTimeout(() => setDeleteConfirm(null), 3000)
    }
  }

  if (isLoading) return <LoadingSkeleton />
  if (error) return <ErrorMessage message="이력을 불러올 수 없습니다." />

  return (
    <div className="max-w-3xl mx-auto py-8 px-4">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">분석 이력</h1>
      {!analyses || analyses.length === 0 ? (
        <div className="text-center py-16">
          <p className="text-gray-400 mb-4">아직 분석 이력이 없습니다.</p>
          <Link to="/" className="text-blue-600 hover:text-blue-700 text-sm font-medium">
            새 분석 시작하기
          </Link>
        </div>
      ) : (
        <div className="space-y-3">
          {analyses.map((a) => (
            <div key={a.id}>
              <AnalysisCard analysis={a} onDelete={handleDelete} />
              {deleteConfirm === a.id && (
                <p className="text-xs text-red-500 mt-1 ml-2">한 번 더 삭제 버튼을 클릭하면 삭제됩니다.</p>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
