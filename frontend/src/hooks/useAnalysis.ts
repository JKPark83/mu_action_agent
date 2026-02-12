import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import type { Analysis, AnalysisDetail } from '../types'

export function useAnalysisList() {
  return useQuery<Analysis[]>({
    queryKey: ['analyses'],
    queryFn: () => api.get('/analyses').then((r) => r.data),
  })
}

export function useAnalysisDetail(id: string | undefined) {
  return useQuery<AnalysisDetail>({
    queryKey: ['analysis', id],
    queryFn: () => api.get(`/analyses/${id}`).then((r) => r.data),
    enabled: !!id,
  })
}
