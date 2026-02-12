interface RightsAnalysisData {
  extinguishment_basis?: string
  assumed_rights?: string[]
  extinguished_rights?: string[]
  tenants?: {
    name: string
    deposit: number
    has_opposition_right: boolean
    has_priority_repayment: boolean
    expected_dividend?: number
  }[]
  risk_level?: string
  risk_factors?: string[]
  total_assumed_amount?: number
}

function formatKRW(value: number): string {
  if (value >= 100_000_000) {
    const eok = Math.floor(value / 100_000_000)
    const man = Math.floor((value % 100_000_000) / 10_000)
    return man > 0 ? `${eok}억 ${man.toLocaleString()}만원` : `${eok}억원`
  }
  return `${Math.floor(value / 10_000).toLocaleString()}만원`
}

const RISK_COLORS: Record<string, string> = {
  HIGH: 'bg-red-100 text-red-800',
  MEDIUM: 'bg-yellow-100 text-yellow-800',
  LOW: 'bg-green-100 text-green-800',
}

export default function RightsAnalysisTab({ data }: { data?: RightsAnalysisData }) {
  if (!data) return <p className="text-sm text-gray-400 py-4">권리분석 데이터가 없습니다.</p>

  return (
    <div className="space-y-6">
      {/* 말소기준 */}
      {data.extinguishment_basis && (
        <div>
          <h4 className="text-sm font-medium text-gray-500 mb-1">말소기준권리</h4>
          <p className="text-sm text-gray-800">{data.extinguishment_basis}</p>
        </div>
      )}

      {/* 위험도 */}
      {data.risk_level && (
        <div className="flex items-center gap-2">
          <span className="text-sm text-gray-500">위험도:</span>
          <span className={`px-2 py-0.5 rounded text-xs font-bold ${RISK_COLORS[data.risk_level] ?? 'bg-gray-100 text-gray-600'}`}>
            {data.risk_level}
          </span>
        </div>
      )}

      {/* 인수/소멸 권리 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <h4 className="text-sm font-medium text-gray-500 mb-2">인수할 권리</h4>
          {data.assumed_rights && data.assumed_rights.length > 0 ? (
            <ul className="space-y-1">
              {data.assumed_rights.map((r, i) => (
                <li key={i} className="text-sm text-red-700 flex items-start gap-1">
                  <span className="shrink-0 mt-1 w-1.5 h-1.5 rounded-full bg-red-400" />
                  {r}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-gray-400">없음</p>
          )}
        </div>
        <div>
          <h4 className="text-sm font-medium text-gray-500 mb-2">소멸할 권리</h4>
          {data.extinguished_rights && data.extinguished_rights.length > 0 ? (
            <ul className="space-y-1">
              {data.extinguished_rights.map((r, i) => (
                <li key={i} className="text-sm text-green-700 flex items-start gap-1">
                  <span className="shrink-0 mt-1 w-1.5 h-1.5 rounded-full bg-green-400" />
                  {r}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-gray-400">없음</p>
          )}
        </div>
      </div>

      {/* 임차인 분석 */}
      {data.tenants && data.tenants.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-gray-500 mb-2">임차인 분석</h4>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-2 px-2 text-gray-500 font-medium">이름</th>
                  <th className="text-right py-2 px-2 text-gray-500 font-medium">보증금</th>
                  <th className="text-center py-2 px-2 text-gray-500 font-medium">대항력</th>
                  <th className="text-center py-2 px-2 text-gray-500 font-medium">우선변제권</th>
                </tr>
              </thead>
              <tbody>
                {data.tenants.map((t, i) => (
                  <tr key={i} className="border-b border-gray-100">
                    <td className="py-2 px-2 text-gray-800">{t.name}</td>
                    <td className="py-2 px-2 text-right text-gray-800">{formatKRW(t.deposit)}</td>
                    <td className="py-2 px-2 text-center">{t.has_opposition_right ? '있음' : '없음'}</td>
                    <td className="py-2 px-2 text-center">{t.has_priority_repayment ? '있음' : '없음'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* 위험 요인 */}
      {data.risk_factors && data.risk_factors.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-gray-500 mb-2">위험 요인</h4>
          <ul className="space-y-1">
            {data.risk_factors.map((f, i) => (
              <li key={i} className="text-sm text-gray-700">
                - {f}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
