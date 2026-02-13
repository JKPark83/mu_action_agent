import axios from 'axios'
import type { Analysis, AnalysisDetail, AnalysisListParams } from '../types'

export const api = axios.create({
  baseURL: '/api/v1',
})

export async function createAnalysis(
  files: File[],
  metadata?: { description?: string; caseNumber?: string },
): Promise<Analysis> {
  // 파일과 메타데이터를 단일 multipart/form-data 요청으로 전송
  const formData = new FormData()
  for (const file of files) {
    formData.append('files', file)
  }
  if (metadata?.description) {
    formData.append('description', metadata.description)
  }
  if (metadata?.caseNumber) {
    formData.append('case_number', metadata.caseNumber)
  }

  const { data: analysis } = await api.post<Analysis>('/analyses', formData)
  return analysis
}

export async function fetchAnalysisStatus(id: string) {
  const { data } = await api.get(`/analyses/${id}/status`)
  return data
}

export async function fetchReport(id: string): Promise<AnalysisDetail> {
  const { data } = await api.get<AnalysisDetail>(`/analyses/${id}`)
  return data
}

export async function deleteAnalysis(id: string): Promise<void> {
  await api.delete(`/analyses/${id}`)
}

export async function fetchAnalyses(params?: AnalysisListParams): Promise<Analysis[]> {
  const { data } = await api.get<Analysis[]>('/analyses', { params })
  return data
}

export async function toggleFavorite(id: string): Promise<{ id: string; is_favorite: boolean }> {
  const { data } = await api.patch<{ id: string; is_favorite: boolean }>(`/analyses/${id}/favorite`)
  return data
}
