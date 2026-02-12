export type AnalysisStatus = 'pending' | 'running' | 'done' | 'error'
export type StageStatus = 'pending' | 'running' | 'done' | 'error'
export type Recommendation = 'recommend' | 'hold' | 'not_recommend'

export interface StageProgress {
  status: StageStatus
  progress: number
}

export interface AnalysisProgress {
  overall: number
  stages: {
    parsed_documents: StageProgress
    rights_analysis: StageProgress
    market_data: StageProgress
    news_analysis: StageProgress
    valuation: StageProgress
    report: StageProgress
  }
}

export interface Analysis {
  id: string
  status: AnalysisStatus
  description: string | null
  case_number: string | null
  created_at: string
  started_at: string | null
  completed_at: string | null
}

export interface AnalysisDetail extends Analysis {
  report: AnalysisReport | null
  rights_analysis: Record<string, unknown> | null
  market_data: Record<string, unknown> | null
  news_analysis: Record<string, unknown> | null
  valuation: Record<string, unknown> | null
}

export interface AnalysisReport {
  recommendation: Recommendation
  reasoning: string
  risk_summary: string
  bid_price: { conservative: number; moderate: number; aggressive: number }
  sale_price: { conservative: number; moderate: number; aggressive: number }
  expected_roi: number
  cost_breakdown?: Record<string, number>
  confidence_score?: number
  disclaimer?: string
  chart_data?: {
    price_trend?: { date: string; price: number }[]
  }
}
