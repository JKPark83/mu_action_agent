import { useState } from 'react'
import { api } from '../api/client'

export function useFileUpload() {
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const upload = async (analysisId: string, files: File[]) => {
    setUploading(true)
    setError(null)
    try {
      for (const file of files) {
        const formData = new FormData()
        formData.append('file', file)
        await api.post(`/files/upload?analysis_id=${analysisId}`, formData)
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : '업로드 실패')
    } finally {
      setUploading(false)
    }
  }

  return { upload, uploading, error }
}
