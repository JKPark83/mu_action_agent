import { useParams } from 'react-router-dom'

export default function Report() {
  const { id } = useParams<{ id: string }>()

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-4">분석 리포트</h1>
      <p className="text-gray-500">분석 ID: {id}</p>
      {/* TODO: 추천카드, 가격비교, 시세차트, 탭 인터페이스 */}
    </div>
  )
}
