import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchAnalyses, toggleFavorite } from '../api/client'
import { api } from '../api/client'
import type { Analysis, AnalysisDetail, AnalysisListParams } from '../types'

export function useAnalysisList(params?: AnalysisListParams) {
  return useQuery<Analysis[]>({
    queryKey: ['analyses', params],
    queryFn: () => fetchAnalyses(params),
  })
}

export function useAnalysisDetail(id: string | undefined) {
  return useQuery<AnalysisDetail>({
    queryKey: ['analysis', id],
    queryFn: () => api.get(`/analyses/${id}`).then((r) => r.data),
    enabled: !!id,
  })
}

export function useToggleFavorite() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => toggleFavorite(id),
    onMutate: async (id) => {
      await queryClient.cancelQueries({ queryKey: ['analyses'] })
      queryClient.setQueriesData<Analysis[]>(
        { queryKey: ['analyses'] },
        (old) => old?.map((a) => (a.id === id ? { ...a, is_favorite: !a.is_favorite } : a)),
      )
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['analyses'] })
    },
  })
}
