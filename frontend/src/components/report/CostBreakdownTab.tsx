interface CostBreakdown {
  acquisition_tax?: number
  registration_fee?: number
  legal_fee?: number
  eviction_cost?: number
  repair_cost?: number
  capital_gains_tax?: number
}

interface CostBreakdownTabProps {
  data?: CostBreakdown
  expectedRoi?: number
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

const COST_LABELS: Record<string, string> = {
  acquisition_tax: '취득세',
  registration_fee: '등록비',
  legal_fee: '법무사 비용',
  eviction_cost: '명도 비용',
  repair_cost: '수리 비용',
  capital_gains_tax: '양도소득세',
}

export default function CostBreakdownTab({ data, expectedRoi }: CostBreakdownTabProps) {
  if (!data) return <p className="text-sm text-gray-400 py-4">비용 데이터가 없습니다.</p>

  const entries = Object.entries(COST_LABELS)
    .filter(([key]) => (data as Record<string, number | undefined>)[key] != null)
    .map(([key, label]) => ({ label, value: (data as Record<string, number>)[key] }))

  const total = entries.reduce((sum, e) => sum + e.value, 0)

  return (
    <div className="space-y-6">
      {/* 비용 항목 */}
      <div>
        <h4 className="text-sm font-medium text-gray-500 mb-3">예상 비용 내역</h4>
        <div className="divide-y divide-gray-100">
          {entries.map(({ label, value }) => (
            <div key={label} className="flex items-center justify-between py-2.5">
              <span className="text-sm text-gray-600">{label}</span>
              <span className="text-sm font-medium text-gray-900">{formatKRW(value)}</span>
            </div>
          ))}
          <div className="flex items-center justify-between py-3">
            <span className="text-sm font-bold text-gray-900">합계</span>
            <span className="text-sm font-bold text-blue-700">{formatKRW(total)}</span>
          </div>
        </div>
      </div>

      {/* 수익률 */}
      {expectedRoi != null && (
        <div className="bg-gray-50 rounded-lg p-4 flex items-center justify-between">
          <span className="text-sm font-medium text-gray-700">예상 수익률</span>
          <span className={`text-lg font-bold ${expectedRoi >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {expectedRoi >= 0 ? '+' : ''}
            {(expectedRoi * 100).toFixed(1)}%
          </span>
        </div>
      )}
    </div>
  )
}
