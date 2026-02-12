import { useParams } from 'react-router-dom'

export default function AnalysisProgress() {
  const { id } = useParams<{ id: string }>()

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-4">분석 진행 현황</h1>
      <p className="text-gray-500">분석 ID: {id}</p>
      {/* TODO: 단계별 진행 상황 시각화 (WebSocket) */}
    </div>
  )
}
