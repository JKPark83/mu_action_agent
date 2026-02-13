import { useState, useMemo, type ChangeEvent } from 'react'

/* ──────────────────────────── Types ──────────────────────────── */

interface PriceRange {
  conservative: number
  moderate: number
  aggressive: number
}

interface InvestmentCalculatorProps {
  bidPrice: PriceRange
  salePrice: PriceRange
  propertyType: string | null
  area: number | null
}

interface CalculatorInputs {
  bidPrice: number
  salePrice: number
  loanPercentage: number
  acquisitionTaxRate: number
  loanInterestRate: number
  movingCost: number
  maintenanceCost: number
  repairCost: number
}

/* ──────────────────────────── Helpers ──────────────────────────── */

function formatKRW(value: number): string {
  const abs = Math.abs(value)
  const sign = value < 0 ? '-' : ''
  if (abs >= 100_000_000) {
    const eok = Math.floor(abs / 100_000_000)
    const man = Math.floor((abs % 100_000_000) / 10_000)
    return sign + (man > 0 ? `${eok}억 ${man.toLocaleString()}만원` : `${eok}억원`)
  }
  if (abs >= 10_000) {
    return sign + `${Math.floor(abs / 10_000).toLocaleString()}만원`
  }
  return sign + `${abs.toLocaleString()}원`
}

function toMan(won: number): number {
  return Math.round(won / 10_000)
}

function fromMan(man: number): number {
  return man * 10_000
}

function isApartment(propertyType: string | null): boolean {
  if (!propertyType) return false
  return ['아파트', '공동주택'].some((k) => propertyType.includes(k))
}

/* ──────────────────────────── Calculator Hook ──────────────────────────── */

function useCalculator(props: InvestmentCalculatorProps) {
  const maxLoanPercentage = isApartment(props.propertyType) ? 70 : 60

  const [inputs, setInputs] = useState<CalculatorInputs>({
    bidPrice: props.bidPrice.moderate,
    salePrice: props.salePrice.moderate,
    loanPercentage: 0,
    acquisitionTaxRate: 1.1,
    loanInterestRate: 5,
    movingCost: 0,
    maintenanceCost: 0,
    repairCost: 0,
  })

  const setInput = (key: keyof CalculatorInputs, value: number) => {
    setInputs((prev) => ({ ...prev, [key]: value }))
  }

  const calculated = useMemo(() => {
    const { bidPrice, salePrice, loanPercentage, acquisitionTaxRate, loanInterestRate, movingCost, maintenanceCost, repairCost } = inputs

    const priceDifference = salePrice - bidPrice
    const loanAmount = Math.round(bidPrice * loanPercentage / 100)

    // 취득비용
    const acquisitionTax = Math.round(bidPrice * acquisitionTaxRate / 100)
    const ruralSpecialTax = (props.area ?? 0) > 85 ? Math.round(bidPrice * 0.002) : 0
    const legalFee = 800_000
    const acquisitionCostTotal = acquisitionTax + ruralSpecialTax + legalFee

    // 대출이자
    const monthlyInterest = Math.round(loanAmount * loanInterestRate / 100 / 12)

    // 명도비용
    const evictionCostTotal = movingCost + maintenanceCost + repairCost

    // 기타 비용
    const brokerageFee = Math.round(salePrice * 0.004)
    const etcCostTotal = brokerageFee

    // 기간별 분석 (0~6개월)
    const equity = bidPrice - loanAmount
    const fixedCosts = acquisitionCostTotal + evictionCostTotal + etcCostTotal
    const periodAnalysis = Array.from({ length: 7 }, (_, months) => {
      const interestCost = months * monthlyInterest
      const actualInvestment = equity + interestCost
      const totalCost = fixedCosts + interestCost
      const netProfit = priceDifference - totalCost
      const returnRate = actualInvestment > 0 ? (netProfit / actualInvestment) * 100 : 0
      return { months, actualInvestment, interestCost, totalCost, netProfit, returnRate }
    })

    return {
      priceDifference,
      loanAmount,
      acquisitionTax,
      ruralSpecialTax,
      legalFee,
      acquisitionCostTotal,
      monthlyInterest,
      evictionCostTotal,
      brokerageFee,
      etcCostTotal,
      fixedCosts,
      periodAnalysis,
    }
  }, [inputs, props.area])

  return { inputs, setInput, calculated, maxLoanPercentage }
}

/* ──────────────────────────── Sub-Components ──────────────────────────── */

function Section({ title, children, total }: { title: string; children: React.ReactNode; total?: { label: string; value: number } }) {
  return (
    <div>
      <h4 className="text-sm font-medium text-gray-500 mb-3">{title}</h4>
      <div className="divide-y divide-gray-100">
        {children}
        {total && (
          <div className="flex items-center justify-between py-3">
            <span className="text-sm font-bold text-gray-900">{total.label}</span>
            <span className="text-sm font-bold text-blue-700">{formatKRW(total.value)}</span>
          </div>
        )}
      </div>
    </div>
  )
}

function Row({ label, value, highlight }: { label: string; value: string; highlight?: boolean }) {
  return (
    <div className="flex items-center justify-between py-2.5">
      <span className="text-sm text-gray-600">{label}</span>
      <span className={`text-sm font-medium ${highlight ? 'text-blue-700 font-bold' : 'text-gray-900'}`}>{value}</span>
    </div>
  )
}

function EditableAmountRow({ label, value, onChange }: { label: string; value: number; onChange: (v: number) => void }) {
  const [editing, setEditing] = useState(false)
  const [tempValue, setTempValue] = useState('')

  const handleClick = () => {
    setTempValue(String(toMan(value)))
    setEditing(true)
  }

  const handleBlur = () => {
    const parsed = parseFloat(tempValue)
    if (!isNaN(parsed)) onChange(fromMan(parsed))
    setEditing(false)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleBlur()
    if (e.key === 'Escape') setEditing(false)
  }

  return (
    <div className="flex items-center justify-between py-2.5">
      <span className="text-sm text-gray-600">{label}</span>
      {editing ? (
        <div className="flex items-center gap-1">
          <input
            type="number"
            value={tempValue}
            onChange={(e) => setTempValue(e.target.value)}
            onBlur={handleBlur}
            onKeyDown={handleKeyDown}
            autoFocus
            className="w-28 text-right text-sm border border-blue-300 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500"
          />
          <span className="text-xs text-gray-500">만원</span>
        </div>
      ) : (
        <button
          onClick={handleClick}
          className="text-sm font-medium text-blue-600 border-b border-dashed border-blue-300 hover:text-blue-800 cursor-pointer"
        >
          {formatKRW(value)}
        </button>
      )}
    </div>
  )
}

function PercentInputRow({ label, value, onChange, step = 0.1 }: { label: string; value: number; onChange: (v: number) => void; step?: number }) {
  const handleChange = (e: ChangeEvent<HTMLInputElement>) => {
    const parsed = parseFloat(e.target.value)
    if (!isNaN(parsed)) onChange(parsed)
  }

  return (
    <div className="flex items-center justify-between py-2.5">
      <span className="text-sm text-gray-600">{label}</span>
      <div className="flex items-center gap-1">
        <input
          type="number"
          value={value}
          onChange={handleChange}
          step={step}
          min={0}
          className="w-20 text-right text-sm border border-gray-300 rounded px-2 py-1 focus:outline-none focus:ring-1 focus:ring-blue-500"
        />
        <span className="text-xs text-gray-500">%</span>
      </div>
    </div>
  )
}

/* ──────────────────────────── Main Component ──────────────────────────── */

export default function InvestmentCalculator({ bidPrice, salePrice, propertyType, area }: InvestmentCalculatorProps) {
  const { inputs, setInput, calculated, maxLoanPercentage } = useCalculator({
    bidPrice,
    salePrice,
    propertyType,
    area,
  })

  const c = calculated

  return (
    <div className="space-y-6">
      {/* ─── 가격 요약 ─── */}
      <Section title="가격 요약">
        <EditableAmountRow label="예상 낙찰가" value={inputs.bidPrice} onChange={(v) => setInput('bidPrice', v)} />
        <EditableAmountRow label="예상 매도액" value={inputs.salePrice} onChange={(v) => setInput('salePrice', v)} />
        <Row
          label="매도차액"
          value={formatKRW(c.priceDifference)}
          highlight
        />
      </Section>

      {/* ─── 대출 설정 ─── */}
      <Section title="대출 설정">
        <div className="py-3">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm text-gray-600">대출비율</span>
            <span className="text-sm font-medium text-gray-900">{inputs.loanPercentage}%</span>
          </div>
          <input
            type="range"
            min={0}
            max={maxLoanPercentage}
            step={5}
            value={inputs.loanPercentage}
            onChange={(e) => setInput('loanPercentage', Number(e.target.value))}
            className="w-full accent-blue-500"
          />
          <div className="flex justify-between text-xs text-gray-400 mt-1">
            <span>0%</span>
            <span>{maxLoanPercentage}% (최대)</span>
          </div>
        </div>
        <Row label="대출금액" value={formatKRW(c.loanAmount)} />
      </Section>

      {/* ─── 취득비용 ─── */}
      <Section title="취득비용" total={{ label: '취득비용 합계', value: c.acquisitionCostTotal }}>
        <PercentInputRow label="취득세율" value={inputs.acquisitionTaxRate} onChange={(v) => setInput('acquisitionTaxRate', v)} />
        <Row label="취득세" value={formatKRW(c.acquisitionTax)} />
        {(area ?? 0) > 85 && <Row label="농어촌특별세" value={formatKRW(c.ruralSpecialTax)} />}
        <Row label="법무사비" value={formatKRW(c.legalFee)} />
      </Section>

      {/* ─── 대출이자비용 ─── */}
      <Section title="대출이자비용">
        <PercentInputRow label="대출이율" value={inputs.loanInterestRate} onChange={(v) => setInput('loanInterestRate', v)} />
        <Row label="월 상환이자" value={formatKRW(c.monthlyInterest)} />
      </Section>

      {/* ─── 명도비용 ─── */}
      <Section title="명도비용" total={{ label: '명도비 합계', value: c.evictionCostTotal }}>
        <EditableAmountRow label="이사비" value={inputs.movingCost} onChange={(v) => setInput('movingCost', v)} />
        <EditableAmountRow label="관리비" value={inputs.maintenanceCost} onChange={(v) => setInput('maintenanceCost', v)} />
        <EditableAmountRow label="수리비" value={inputs.repairCost} onChange={(v) => setInput('repairCost', v)} />
      </Section>

      {/* ─── 기타 비용 ─── */}
      <Section title="기타 비용" total={{ label: '기타 비용 합계', value: c.etcCostTotal }}>
        <Row label="부동산중개비 (매도액의 0.4%)" value={formatKRW(c.brokerageFee)} />
      </Section>

      {/* ─── 기간별 수익 분석 ─── */}
      <div>
        <h4 className="text-sm font-medium text-gray-500 mb-3">기간별 수익 분석</h4>

        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left py-2 pr-4 text-gray-500 font-medium whitespace-nowrap">보유기간</th>
                {c.periodAnalysis.map((p) => (
                  <th key={p.months} className="text-right py-2 px-2 text-gray-500 font-medium whitespace-nowrap">
                    {p.months}개월
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              <tr className="border-b border-gray-100">
                <td className="py-2 pr-4 text-gray-600 whitespace-nowrap">실투자금</td>
                {c.periodAnalysis.map((p) => (
                  <td key={p.months} className="text-right py-2 px-2 text-gray-900 font-medium whitespace-nowrap">
                    {formatKRW(p.actualInvestment)}
                  </td>
                ))}
              </tr>
              <tr className="border-b border-gray-100">
                <td className="py-2 pr-4 text-gray-600 whitespace-nowrap">매도차액</td>
                {c.periodAnalysis.map((p) => (
                  <td key={p.months} className="text-right py-2 px-2 text-gray-900 font-medium whitespace-nowrap">
                    {formatKRW(c.priceDifference)}
                  </td>
                ))}
              </tr>
              <tr className="border-b border-gray-100">
                <td className="py-2 pr-4 text-gray-500 whitespace-nowrap pl-3">취득비용</td>
                {c.periodAnalysis.map((p) => (
                  <td key={p.months} className="text-right py-2 px-2 text-gray-500 whitespace-nowrap">
                    {formatKRW(c.acquisitionCostTotal)}
                  </td>
                ))}
              </tr>
              <tr className="border-b border-gray-100">
                <td className="py-2 pr-4 text-gray-500 whitespace-nowrap pl-3">명도비용</td>
                {c.periodAnalysis.map((p) => (
                  <td key={p.months} className="text-right py-2 px-2 text-gray-500 whitespace-nowrap">
                    {formatKRW(c.evictionCostTotal)}
                  </td>
                ))}
              </tr>
              <tr className="border-b border-gray-100">
                <td className="py-2 pr-4 text-gray-500 whitespace-nowrap pl-3">기타 비용</td>
                {c.periodAnalysis.map((p) => (
                  <td key={p.months} className="text-right py-2 px-2 text-gray-500 whitespace-nowrap">
                    {formatKRW(c.etcCostTotal)}
                  </td>
                ))}
              </tr>
              <tr className="border-b border-gray-100">
                <td className="py-2 pr-4 text-gray-500 whitespace-nowrap pl-3">대출이자</td>
                {c.periodAnalysis.map((p) => (
                  <td key={p.months} className="text-right py-2 px-2 text-gray-500 whitespace-nowrap">
                    {formatKRW(p.interestCost)}
                  </td>
                ))}
              </tr>
              <tr className="border-b border-gray-100 bg-gray-50">
                <td className="py-2 pr-4 text-gray-700 font-medium whitespace-nowrap">총 비용</td>
                {c.periodAnalysis.map((p) => (
                  <td key={p.months} className="text-right py-2 px-2 text-gray-700 font-medium whitespace-nowrap">
                    {formatKRW(p.totalCost)}
                  </td>
                ))}
              </tr>
              <tr className="border-b border-gray-200">
                <td className="py-2.5 pr-4 font-bold text-gray-900 whitespace-nowrap">실수익금</td>
                {c.periodAnalysis.map((p) => (
                  <td
                    key={p.months}
                    className={`text-right py-2.5 px-2 font-bold whitespace-nowrap ${
                      p.netProfit >= 0 ? 'text-green-600' : 'text-red-600'
                    }`}
                  >
                    {formatKRW(p.netProfit)}
                  </td>
                ))}
              </tr>
              <tr>
                <td className="py-2.5 pr-4 font-bold text-gray-900 whitespace-nowrap">수익률</td>
                {c.periodAnalysis.map((p) => (
                  <td
                    key={p.months}
                    className={`text-right py-2.5 px-2 font-bold whitespace-nowrap ${
                      p.returnRate >= 0 ? 'text-green-600' : 'text-red-600'
                    }`}
                  >
                    {p.actualInvestment > 0
                      ? `${p.returnRate >= 0 ? '+' : ''}${p.returnRate.toFixed(1)}%`
                      : 'N/A'}
                  </td>
                ))}
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
