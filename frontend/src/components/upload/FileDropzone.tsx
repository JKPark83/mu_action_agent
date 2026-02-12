import { useCallback, useRef, useState } from 'react'

interface FileDropzoneProps {
  onFilesSelected: (files: File[]) => void
  maxFiles?: number
  maxSizeMB?: number
}

export default function FileDropzone({ onFilesSelected, maxFiles = 10, maxSizeMB = 50 }: FileDropzoneProps) {
  const [isDragging, setIsDragging] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const validateFiles = useCallback(
    (files: File[]): File[] => {
      setError(null)
      const valid: File[] = []
      for (const file of files) {
        if (file.type !== 'application/pdf') {
          setError('PDF 파일만 업로드할 수 있습니다.')
          continue
        }
        if (file.size > maxSizeMB * 1024 * 1024) {
          setError(`파일 크기는 ${maxSizeMB}MB 이하여야 합니다.`)
          continue
        }
        valid.push(file)
      }
      if (valid.length > maxFiles) {
        setError(`최대 ${maxFiles}개의 파일만 업로드할 수 있습니다.`)
        return valid.slice(0, maxFiles)
      }
      return valid
    },
    [maxFiles, maxSizeMB],
  )

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setIsDragging(false)
      const files = validateFiles(Array.from(e.dataTransfer.files))
      if (files.length > 0) onFilesSelected(files)
    },
    [onFilesSelected, validateFiles],
  )

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (!e.target.files) return
      const files = validateFiles(Array.from(e.target.files))
      if (files.length > 0) onFilesSelected(files)
      e.target.value = ''
    },
    [onFilesSelected, validateFiles],
  )

  return (
    <div>
      <div
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault()
          setIsDragging(true)
        }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-colors ${
          isDragging ? 'border-blue-500 bg-blue-50' : 'border-gray-300 hover:border-gray-400 bg-white'
        }`}
      >
        <div className="flex flex-col items-center gap-3">
          <svg className="w-12 h-12 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={1.5}
              d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
            />
          </svg>
          <p className="text-gray-600 font-medium">PDF 파일을 드래그하거나 클릭하여 선택하세요</p>
          <p className="text-sm text-gray-400">최대 {maxSizeMB}MB, {maxFiles}개 파일</p>
        </div>
        <input ref={inputRef} type="file" accept=".pdf" multiple className="hidden" onChange={handleFileChange} />
      </div>
      {error && <p className="mt-2 text-sm text-red-500">{error}</p>}
    </div>
  )
}
