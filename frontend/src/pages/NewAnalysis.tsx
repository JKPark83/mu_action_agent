import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { createAnalysis } from '../api/client'
import FileDropzone from '../components/upload/FileDropzone'
import FileList from '../components/upload/FileList'
import UploadForm from '../components/upload/UploadForm'

export default function NewAnalysis() {
  const [files, setFiles] = useState<File[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()

  const handleSubmit = async (metadata: { description?: string; caseNumber?: string }) => {
    if (files.length === 0) {
      setError('PDF 파일을 먼저 선택해주세요.')
      return
    }
    setIsLoading(true)
    setError(null)
    try {
      const analysis = await createAnalysis(files, metadata)
      navigate(`/analysis/${analysis.id}`)
    } catch (e) {
      setError(e instanceof Error ? e.message : '분석 시작에 실패했습니다.')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="max-w-2xl mx-auto py-8 px-4">
      <div className="text-center mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">부동산 경매 분석 AI</h1>
        <p className="text-gray-500">경매 관련 PDF 문서를 업로드하면 AI가 종합 분석해드립니다.</p>
      </div>
      <div className="space-y-6">
        <FileDropzone onFilesSelected={(f) => setFiles((prev) => [...prev, ...f])} />
        <FileList files={files} onRemove={(i) => setFiles((prev) => prev.filter((_, idx) => idx !== i))} />
        {error && <p className="text-sm text-red-500 text-center">{error}</p>}
        <UploadForm onSubmit={handleSubmit} isLoading={isLoading} disabled={files.length === 0} />
      </div>
    </div>
  )
}
