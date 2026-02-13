interface RightsAnalysisData {
  extinguishment_basis?: string
  assumed_rights?: string[]
  extinguished_rights?: string[]
  tenants?: {
    name: string
    deposit: number
    has_opposition_right: boolean
    has_priority_repayment: boolean
    move_in_date?: string
    confirmed_date?: string
    dividend_applied?: boolean
    dividend_ranking?: number | null
    expected_dividend?: number
  }[]
  risk_level?: string
  risk_factors?: string[]
  total_assumed_amount?: number
  total_assumed_deposit?: number
}

function formatKRW(value: number): string {
  if (value >= 100_000_000) {
    const eok = Math.floor(value / 100_000_000)
    const man = Math.floor((value % 100_000_000) / 10_000)
    return man > 0 ? `${eok}억 ${man.toLocaleString()}만원` : `${eok}억원`
  }
  return `${Math.floor(value / 10_000).toLocaleString()}만원`
}

function formatDate(date?: string): string {
  if (!date) return '-'
  return date
}

function formatRanking(ranking?: number | null): string {
  if (ranking === null || ranking === undefined) return '-'
  if (ranking === 0) return '최우선'
  return `${ranking}순위`
}

const RISK_COLORS: Record<string, { className: string; label: string }> = {
  high: { className: 'bg-red-100 text-red-800', label: '높음' },
  medium: { className: 'bg-yellow-100 text-yellow-800', label: '보통' },
  low: { className: 'bg-green-100 text-green-800', label: '낮음' },
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
          <span className={`px-2 py-0.5 rounded text-xs font-bold ${RISK_COLORS[data.risk_level]?.className ?? 'bg-gray-100 text-gray-600'}`}>
            {RISK_COLORS[data.risk_level]?.label ?? data.risk_level}
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
                  <th className="text-center py-2 px-2 text-gray-500 font-medium">전입일</th>
                  <th className="text-center py-2 px-2 text-gray-500 font-medium">확정일</th>
                  <th className="text-center py-2 px-2 text-gray-500 font-medium">대항력</th>
                  <th className="text-center py-2 px-2 text-gray-500 font-medium">배당신청</th>
                  <th className="text-center py-2 px-2 text-gray-500 font-medium">배당순위</th>
                </tr>
              </thead>
              <tbody>
                {data.tenants.map((t, i) => (
                  <tr key={i} className="border-b border-gray-100">
                    <td className="py-2 px-2 text-gray-800">{t.name}</td>
                    <td className="py-2 px-2 text-right text-gray-800">{formatKRW(t.deposit)}</td>
                    <td className="py-2 px-2 text-center text-gray-600">{formatDate(t.move_in_date)}</td>
                    <td className="py-2 px-2 text-center text-gray-600">{formatDate(t.confirmed_date)}</td>
                    <td className="py-2 px-2 text-center">
                      <span className={t.has_opposition_right ? 'text-red-600 font-medium' : 'text-gray-400'}>
                        {t.has_opposition_right ? '있음' : '없음'}
                      </span>
                    </td>
                    <td className="py-2 px-2 text-center">
                      <span className={t.dividend_applied ? 'text-blue-600 font-medium' : 'text-gray-400'}>
                        {t.dividend_applied ? '신청' : '미신청'}
                      </span>
                    </td>
                    <td className="py-2 px-2 text-center">
                      <span className={t.dividend_ranking !== null && t.dividend_ranking !== undefined
                        ? (t.dividend_ranking === 0 ? 'text-purple-600 font-bold' : 'text-blue-600 font-medium')
                        : 'text-gray-400'}>
                        {formatRanking(t.dividend_ranking)}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* 대항력 있는 임차인 인수 보증금 합계 */}
          {(data.total_assumed_deposit ?? 0) > 0 && (
            <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg">
              <p className="text-sm text-red-800">
                <span className="font-medium">대항력 있는 임차인 인수 보증금 합계:</span>{' '}
                <span className="font-bold">{formatKRW(data.total_assumed_deposit!)}</span>
              </p>
            </div>
          )}
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
