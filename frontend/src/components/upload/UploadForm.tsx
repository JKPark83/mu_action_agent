import { useState } from 'react'
import { Spinner } from '../common/Loading'

interface UploadFormProps {
  onSubmit: (metadata: { description?: string; caseNumber?: string }) => void
  isLoading: boolean
  disabled?: boolean
}

export default function UploadForm({ onSubmit, isLoading, disabled }: UploadFormProps) {
  const [caseNumber, setCaseNumber] = useState('')
  const [description, setDescription] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    onSubmit({
      caseNumber: caseNumber.trim() || undefined,
      description: description.trim() || undefined,
    })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label htmlFor="caseNumber" className="block text-sm font-medium text-gray-700 mb-1">
          사건번호 (선택)
        </label>
        <input
          id="caseNumber"
          type="text"
          value={caseNumber}
          onChange={(e) => setCaseNumber(e.target.value)}
          placeholder="예: 2023타경12345"
          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
        />
      </div>
      <div>
        <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-1">
          메모 (선택)
        </label>
        <input
          id="description"
          type="text"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          placeholder="분석에 대한 메모를 입력하세요"
          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none"
        />
      </div>
      <button
        type="submit"
        disabled={disabled || isLoading}
        className="w-full py-3 px-4 bg-blue-600 text-white font-medium rounded-lg hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
      >
        {isLoading ? (
          <>
            <Spinner className="h-4 w-4 text-white" />
            분석 시작 중...
          </>
        ) : (
          '분석 시작'
        )}
      </button>
    </form>
  )
}
