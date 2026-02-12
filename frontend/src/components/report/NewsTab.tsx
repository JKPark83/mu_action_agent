interface NewsData {
  positive_factors?: string[]
  negative_factors?: string[]
  market_trend_summary?: string
  area_attractiveness_score?: number
  investment_opinion?: string
  outlook_6month?: string
}

export default function NewsTab({ data }: { data?: NewsData }) {
  if (!data) return <p className="text-sm text-gray-400 py-4">뉴스 분석 데이터가 없습니다.</p>

  return (
    <div className="space-y-6">
      {/* 시장 요약 */}
      {data.market_trend_summary && (
        <div>
          <h4 className="text-sm font-medium text-gray-500 mb-1">시장 동향 요약</h4>
          <p className="text-sm text-gray-800 leading-relaxed">{data.market_trend_summary}</p>
        </div>
      )}

      {/* 호재/악재 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <h4 className="text-sm font-medium text-green-600 mb-2">호재 요인</h4>
          {data.positive_factors && data.positive_factors.length > 0 ? (
            <ul className="space-y-1">
              {data.positive_factors.map((f, i) => (
                <li key={i} className="text-sm text-gray-700 flex items-start gap-2">
                  <span className="text-green-500 shrink-0">+</span>
                  {f}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-gray-400">특이사항 없음</p>
          )}
        </div>
        <div>
          <h4 className="text-sm font-medium text-red-600 mb-2">악재 요인</h4>
          {data.negative_factors && data.negative_factors.length > 0 ? (
            <ul className="space-y-1">
              {data.negative_factors.map((f, i) => (
                <li key={i} className="text-sm text-gray-700 flex items-start gap-2">
                  <span className="text-red-500 shrink-0">-</span>
                  {f}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-gray-400">특이사항 없음</p>
          )}
        </div>
      </div>

      {/* 지표 */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {data.area_attractiveness_score != null && (
          <div className="bg-gray-50 rounded-lg p-3">
            <p className="text-xs text-gray-500">지역 매력도</p>
            <p className="text-sm font-bold text-gray-900">{(data.area_attractiveness_score * 10).toFixed(1)} / 10</p>
          </div>
        )}
        {data.outlook_6month && (
          <div className="bg-gray-50 rounded-lg p-3">
            <p className="text-xs text-gray-500">6개월 전망</p>
            <p className="text-sm font-bold text-gray-900">{data.outlook_6month}</p>
          </div>
        )}
      </div>

      {/* 투자 의견 */}
      {data.investment_opinion && (
        <div>
          <h4 className="text-sm font-medium text-gray-500 mb-1">투자 의견</h4>
          <p className="text-sm text-gray-800 leading-relaxed">{data.investment_opinion}</p>
        </div>
      )}
    </div>
  )
}
