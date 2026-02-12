interface Transaction {
  address: string
  area: number
  price: number
  price_per_pyeong: number
  transaction_date: string
}

interface MarketData {
  recent_transactions?: Transaction[]
  avg_price_per_pyeong?: number
  price_range_low?: number
  price_range_high?: number
  price_trend?: string
  jeonse_ratio?: number
}

function formatKRW(value: number): string {
  if (value >= 100_000_000) {
    const eok = Math.floor(value / 100_000_000)
    const man = Math.floor((value % 100_000_000) / 10_000)
    return man > 0 ? `${eok}억 ${man.toLocaleString()}만` : `${eok}억`
  }
  return `${Math.floor(value / 10_000).toLocaleString()}만`
}

const TREND_LABELS: Record<string, { label: string; className: string }> = {
  상승: { label: '상승', className: 'text-red-600' },
  보합: { label: '보합', className: 'text-gray-600' },
  하락: { label: '하락', className: 'text-blue-600' },
}

export default function MarketDataTab({ data }: { data?: MarketData }) {
  if (!data) return <p className="text-sm text-gray-400 py-4">시세 데이터가 없습니다.</p>

  const trend = data.price_trend ? TREND_LABELS[data.price_trend] : null

  return (
    <div className="space-y-6">
      {/* 요약 지표 */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {data.avg_price_per_pyeong != null && (
          <div className="bg-gray-50 rounded-lg p-3">
            <p className="text-xs text-gray-500">평당 평균가</p>
            <p className="text-sm font-bold text-gray-900">{formatKRW(data.avg_price_per_pyeong)}원</p>
          </div>
        )}
        {data.price_range_low != null && data.price_range_high != null && (
          <div className="bg-gray-50 rounded-lg p-3">
            <p className="text-xs text-gray-500">가격 범위</p>
            <p className="text-sm font-bold text-gray-900">
              {formatKRW(data.price_range_low)} ~ {formatKRW(data.price_range_high)}
            </p>
          </div>
        )}
        {trend && (
          <div className="bg-gray-50 rounded-lg p-3">
            <p className="text-xs text-gray-500">시세 추세</p>
            <p className={`text-sm font-bold ${trend.className}`}>{trend.label}</p>
          </div>
        )}
        {data.jeonse_ratio != null && (
          <div className="bg-gray-50 rounded-lg p-3">
            <p className="text-xs text-gray-500">전세가율</p>
            <p className="text-sm font-bold text-gray-900">{(data.jeonse_ratio * 100).toFixed(1)}%</p>
          </div>
        )}
      </div>

      {/* 거래 이력 */}
      {data.recent_transactions && data.recent_transactions.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-gray-500 mb-2">최근 거래 이력</h4>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-2 px-2 text-gray-500 font-medium">거래일</th>
                  <th className="text-left py-2 px-2 text-gray-500 font-medium">주소</th>
                  <th className="text-right py-2 px-2 text-gray-500 font-medium">면적(㎡)</th>
                  <th className="text-right py-2 px-2 text-gray-500 font-medium">거래가</th>
                  <th className="text-right py-2 px-2 text-gray-500 font-medium">평당가</th>
                </tr>
              </thead>
              <tbody>
                {data.recent_transactions.map((tx, i) => (
                  <tr key={i} className="border-b border-gray-100">
                    <td className="py-2 px-2 text-gray-600">{tx.transaction_date}</td>
                    <td className="py-2 px-2 text-gray-800 truncate max-w-48">{tx.address}</td>
                    <td className="py-2 px-2 text-right text-gray-600">{tx.area}</td>
                    <td className="py-2 px-2 text-right font-medium text-gray-900">{formatKRW(tx.price)}원</td>
                    <td className="py-2 px-2 text-right text-gray-600">{formatKRW(tx.price_per_pyeong)}원</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
