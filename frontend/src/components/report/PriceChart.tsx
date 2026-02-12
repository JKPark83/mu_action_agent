import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

interface PriceDataPoint {
  date: string
  price: number
}

interface PriceChartProps {
  data: PriceDataPoint[]
  appraisedValue?: number
}

function formatMan(value: number): string {
  if (value >= 10000) return `${(value / 10000).toFixed(0)}억`
  return `${value.toLocaleString()}만`
}

export default function PriceChart({ data, appraisedValue }: PriceChartProps) {
  if (!data || data.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">시세 추이</h3>
        <p className="text-sm text-gray-400 text-center py-8">시세 데이터가 없습니다.</p>
      </div>
    )
  }

  // 만원 단위로 변환
  const chartData = data.map((d) => ({ ...d, priceMan: Math.round(d.price / 10000) }))
  const appraisedMan = appraisedValue ? Math.round(appraisedValue / 10000) : undefined

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">시세 추이</h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={chartData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis dataKey="date" tick={{ fontSize: 12 }} stroke="#9ca3af" />
          <YAxis tickFormatter={formatMan} tick={{ fontSize: 12 }} stroke="#9ca3af" />
          <Tooltip
            formatter={(value) => [`${formatMan(Number(value))}원`, '평균 거래가']}
            labelStyle={{ color: '#374151' }}
          />
          <Line type="monotone" dataKey="priceMan" stroke="#3b82f6" strokeWidth={2} dot={{ r: 3 }} />
          {appraisedMan && (
            <Line
              type="monotone"
              dataKey={() => appraisedMan}
              stroke="#ef4444"
              strokeWidth={1}
              strokeDasharray="5 5"
              dot={false}
              name="감정가"
            />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
