import { useState, useMemo } from 'react'
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

interface PriceDataPoint {
  date: string
  price: number
}

interface PriceChartProps {
  data: PriceDataPoint[]
  appraisedValue?: number
}

type Period = '3Y' | '5Y' | 'MAX'

const PERIODS: { key: Period; label: string }[] = [
  { key: '3Y', label: '3년' },
  { key: '5Y', label: '5년' },
  { key: 'MAX', label: '전체' },
]

function formatMan(value: number): string {
  if (value >= 10000) return `${(value / 10000).toFixed(0)}억`
  return `${value.toLocaleString()}만`
}

/** 기간 필터 적용 후 cutoff 날짜 문자열("YYYY-MM") 반환 */
function getCutoffDate(period: Period): string {
  if (period === 'MAX') return '0000-00'
  const now = new Date()
  const years = period === '3Y' ? 3 : 5
  const cutoff = new Date(now.getFullYear() - years, now.getMonth(), 1)
  return `${cutoff.getFullYear()}-${String(cutoff.getMonth() + 1).padStart(2, '0')}`
}

/** 데이터 범위가 7년 이상인지 판단 */
function spansOverYears(data: PriceDataPoint[], years: number): boolean {
  if (data.length < 2) return false
  const first = data[0].date
  const last = data[data.length - 1].date
  const firstYear = parseInt(first.substring(0, 4), 10)
  const lastYear = parseInt(last.substring(0, 4), 10)
  const firstMonth = parseInt(first.substring(5, 7), 10)
  const lastMonth = parseInt(last.substring(5, 7), 10)
  return (lastYear - firstYear) + (lastMonth - firstMonth) / 12 >= years
}

/** 월별 데이터를 연별 평균으로 집계 */
function aggregateToYearly(data: PriceDataPoint[]): PriceDataPoint[] {
  const yearly: Record<string, { sum: number; count: number }> = {}
  for (const d of data) {
    const year = d.date.substring(0, 4)
    if (!yearly[year]) yearly[year] = { sum: 0, count: 0 }
    yearly[year].sum += d.price
    yearly[year].count++
  }
  return Object.entries(yearly)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([year, { sum, count }]) => ({
      date: year,
      price: Math.round(sum / count),
    }))
}

export default function PriceChart({ data, appraisedValue }: PriceChartProps) {
  const [period, setPeriod] = useState<Period>('MAX')

  const { chartData, isYearly, rangeLabel } = useMemo(() => {
    if (!data || data.length === 0) return { chartData: [], isYearly: false, rangeLabel: '' }

    const cutoff = getCutoffDate(period)
    const filtered = data.filter((d) => d.date >= cutoff)

    if (filtered.length === 0) return { chartData: [], isYearly: false, rangeLabel: '' }

    const first = filtered[0].date
    const last = filtered[filtered.length - 1].date
    const label = `${first} ~ ${last} (${filtered.length}개월)`

    // 7년 이상이면 연단위 평균으로 집계
    if (spansOverYears(filtered, 7)) {
      const yearly = aggregateToYearly(filtered)
      return {
        chartData: yearly.map((d) => ({ ...d, priceMan: Math.round(d.price / 10000) })),
        isYearly: true,
        rangeLabel: label,
      }
    }

    return {
      chartData: filtered.map((d) => ({ ...d, priceMan: Math.round(d.price / 10000) })),
      isYearly: false,
      rangeLabel: label,
    }
  }, [data, period])

  if (!data || data.length === 0) {
    return (
      <div className="bg-white rounded-xl border border-gray-200 p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">시세 추이</h3>
        <p className="text-sm text-gray-400 text-center py-8">시세 데이터가 없습니다.</p>
      </div>
    )
  }

  const appraisedMan = appraisedValue ? Math.round(appraisedValue / 10000) : undefined

  /** X축 라벨: 월별이면 "24.01", 연별이면 "2020" */
  const formatXAxis = (value: string) => {
    if (isYearly) return value
    // "YYYY-MM" → "YY.MM"
    if (value.length >= 7) {
      return `${value.substring(2, 4)}.${value.substring(5, 7)}`
    }
    return value
  }

  // 데이터 포인트가 많을 때 X축 라벨 간격 조절
  const tickInterval = chartData.length > 24 ? Math.floor(chartData.length / 12) - 1 : 0

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-gray-900">시세 추이</h3>
        <div className="flex gap-1">
          {PERIODS.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setPeriod(key)}
              className={`px-3 py-1 text-xs font-medium rounded-md transition-colors ${
                period === key
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
      {rangeLabel && (
        <p className="text-xs text-gray-400 mb-2">
          {rangeLabel}
          {isYearly && ' (연단위 평균)'}
        </p>
      )}
      {chartData.length === 0 ? (
        <p className="text-sm text-gray-400 text-center py-16">
          선택한 기간 내 거래 데이터가 없습니다. 다른 기간을 선택해 주세요.
        </p>
      ) : (
        <ResponsiveContainer width="100%" height={300}>
          <LineChart data={chartData} margin={{ top: 5, right: 20, left: 10, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
            <XAxis
              dataKey="date"
              tickFormatter={formatXAxis}
              tick={{ fontSize: 11 }}
              stroke="#9ca3af"
              interval={tickInterval}
            />
            <YAxis tickFormatter={formatMan} tick={{ fontSize: 12 }} stroke="#9ca3af" />
            <Tooltip
              formatter={(value) => [`${formatMan(Number(value))}원`, isYearly ? '연평균 거래가' : '월평균 거래가']}
              labelFormatter={(label) =>
                isYearly ? `${label}년` : label.length >= 7 ? `${label.substring(0, 4)}년 ${label.substring(5)}월` : label
              }
              labelStyle={{ color: '#374151' }}
            />
            <Line type="monotone" dataKey="priceMan" stroke="#3b82f6" strokeWidth={2} dot={{ r: 2 }} activeDot={{ r: 5 }} />
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
      )}
    </div>
  )
}
