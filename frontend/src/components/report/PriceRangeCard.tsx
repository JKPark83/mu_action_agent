interface PriceRange {
  conservative: number
  moderate: number
  aggressive: number
}

interface PriceRangeCardProps {
  bidPrice: PriceRange
  salePrice: PriceRange
  minimumSalePrice?: number
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

function PriceRow({ label, value, highlight }: { label: string; value: number; highlight?: boolean }) {
  return (
    <div className="flex items-center justify-between py-2">
      <span className="text-sm text-gray-600">{label}</span>
      <span className={`text-sm font-semibold ${highlight ? 'text-blue-700' : 'text-gray-900'}`}>
        {formatKRW(value)}
      </span>
    </div>
  )
}

export default function PriceRangeCard({ bidPrice, salePrice, minimumSalePrice }: PriceRangeCardProps) {
  return (
    <div className="bg-white rounded-xl border border-gray-200 p-6">
      <h3 className="text-lg font-semibold text-gray-900 mb-4">가격 분석</h3>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* 입찰 적정가 */}
        <div>
          <h4 className="text-sm font-medium text-gray-500 mb-2">입찰 적정가</h4>
          <div className="divide-y divide-gray-100">
            <PriceRow label="보수적" value={bidPrice.conservative} />
            <PriceRow label="적정" value={bidPrice.moderate} highlight />
            <PriceRow label="공격적" value={bidPrice.aggressive} />
          </div>
        </div>
        {/* 매도 적정가 */}
        <div>
          <h4 className="text-sm font-medium text-gray-500 mb-2">매도 적정가</h4>
          <div className="divide-y divide-gray-100">
            <PriceRow label="비관적" value={salePrice.conservative} />
            <PriceRow label="기본" value={salePrice.moderate} highlight />
            <PriceRow label="낙관적" value={salePrice.aggressive} />
          </div>
        </div>
      </div>
      {minimumSalePrice != null && (
        <div className="mt-4 pt-4 border-t border-gray-200 flex items-center justify-between">
          <span className="text-sm text-gray-500">최저매각가격</span>
          <span className="text-sm font-bold text-gray-900">{formatKRW(minimumSalePrice)}</span>
        </div>
      )}
    </div>
  )
}
