import axios from 'axios'
import type { Analysis, AnalysisDetail } from '../types'

export const api = axios.create({
  baseURL: '/api/v1',
})

export async function createAnalysis(
  files: File[],
  metadata?: { description?: string; caseNumber?: string },
): Promise<Analysis> {
  // 1. 분석 생성
  const { data: analysis } = await api.post<Analysis>('/analyses', {
    description: metadata?.description,
    case_number: metadata?.caseNumber,
  })

  // 2. 파일 업로드
  for (const file of files) {
    const formData = new FormData()
    formData.append('file', file)
    await api.post(`/files/upload?analysis_id=${analysis.id}`, formData)
  }

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
