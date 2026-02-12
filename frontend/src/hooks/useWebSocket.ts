import { useEffect, useRef, useState } from 'react'
import type { AnalysisProgress, StageProgress } from '../types'

// 백엔드 WS stage 이름 → 프론트엔드 stage 키 매핑
const WS_STAGE_MAP: Record<string, string> = {
  document_parser: 'parsed_documents',
  rights_analysis: 'rights_analysis',
  market_data: 'market_data',
  news_analysis: 'news_analysis',
  valuation: 'valuation',
  report_generator: 'report',
}

const ALL_STAGES = [
  'parsed_documents',
  'rights_analysis',
  'market_data',
  'news_analysis',
  'valuation',
  'report',
]

function buildProgress(stages: Record<string, StageProgress>): AnalysisProgress {
  let doneCount = 0
  for (const key of ALL_STAGES) {
    if (stages[key]?.status === 'done') doneCount++
  }
  const overall = Math.round((doneCount / ALL_STAGES.length) * 100)
  return { overall, stages } as AnalysisProgress
}

export function useWebSocket(analysisId: string | undefined) {
  const wsRef = useRef<WebSocket | null>(null)
  const stagesRef = useRef<Record<string, StageProgress>>({})
  const [progress, setProgress] = useState<AnalysisProgress | null>(null)
  const [isComplete, setIsComplete] = useState(false)

  useEffect(() => {
    if (!analysisId) return

    // 초기화
    stagesRef.current = {}
    for (const key of ALL_STAGES) {
      stagesRef.current[key] = { status: 'pending', progress: 0 }
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const ws = new WebSocket(`${protocol}//${window.location.host}/api/v1/ws/analyses/${analysisId}`)
    wsRef.current = ws

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)

      if (data.type === 'analysis_complete') {
        for (const key of ALL_STAGES) {
          stagesRef.current[key] = { status: 'done', progress: 100 }
        }
        setProgress(buildProgress(stagesRef.current))
        setIsComplete(true)
      } else if (data.type === 'analysis_error') {
        setIsComplete(true)
      } else if (data.type === 'status_update') {
        const frontendKey = WS_STAGE_MAP[data.stage] ?? data.stage
        stagesRef.current[frontendKey] = {
          status: data.status,
          progress: data.progress,
        }
        setProgress(buildProgress({ ...stagesRef.current }))
      }
    }

    return () => {
      ws.close()
    }
  }, [analysisId])

  return { progress, isComplete }
}
