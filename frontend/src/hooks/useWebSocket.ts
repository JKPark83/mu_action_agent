import { useEffect, useRef, useState } from 'react'
import type { AnalysisProgress } from '../types'

export function useWebSocket(analysisId: string | undefined) {
  const wsRef = useRef<WebSocket | null>(null)
  const [progress, setProgress] = useState<AnalysisProgress | null>(null)
  const [isComplete, setIsComplete] = useState(false)

  useEffect(() => {
    if (!analysisId) return

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const ws = new WebSocket(`${protocol}//${window.location.host}/ws/analyses/${analysisId}`)
    wsRef.current = ws

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      if (data.type === 'analysis_complete') {
        setIsComplete(true)
      } else {
        setProgress(data)
        // overall 100%면 완료
        if (data.overall >= 100) {
          setIsComplete(true)
        }
      }
    }

    return () => {
      ws.close()
    }
  }, [analysisId])

  return { progress, isComplete }
}
