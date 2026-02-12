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
    document_parsing: StageProgress
    rights_analysis: StageProgress
    market_data: StageProgress
    news_analysis: StageProgress
    valuation: StageProgress
    report_generation: StageProgress
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
}

export interface AnalysisReport {
  recommendation: Recommendation
  bid_price: { conservative: number; moderate: number; aggressive: number }
  sale_price: { conservative: number; moderate: number; aggressive: number }
  expected_roi: number
  risk_summary: string
  reasoning: string
}
