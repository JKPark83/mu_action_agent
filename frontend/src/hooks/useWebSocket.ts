import { useEffect, useRef, useState } from 'react'
import type { AnalysisProgress } from '../types'

export function useWebSocket(analysisId: string | undefined) {
  const wsRef = useRef<WebSocket | null>(null)
  const [progress, setProgress] = useState<AnalysisProgress | null>(null)

  useEffect(() => {
    if (!analysisId) return

    const ws = new WebSocket(`ws://${window.location.host}/ws/analyses/${analysisId}`)
    wsRef.current = ws

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data)
      setProgress(data)
    }

    return () => {
      ws.close()
    }
  }, [analysisId])

  return { progress }
}
