interface FileListProps {
  files: File[]
  onRemove: (index: number) => void
}

function formatSize(bytes: number): string {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export default function FileList({ files, onRemove }: FileListProps) {
  if (files.length === 0) {
    return <p className="text-sm text-gray-400 text-center py-4">선택된 파일이 없습니다.</p>
  }

  return (
    <ul className="divide-y divide-gray-100">
      {files.map((file, index) => (
        <li key={`${file.name}-${index}`} className="flex items-center justify-between py-3 px-2">
          <div className="flex items-center gap-3 min-w-0">
            <svg className="w-5 h-5 text-red-500 shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path d="M4 18h12a2 2 0 002-2V6l-4-4H4a2 2 0 00-2 2v12a2 2 0 002 2zm6-10V3l5 5h-5z" />
            </svg>
            <div className="min-w-0">
              <p className="text-sm font-medium text-gray-700 truncate">{file.name}</p>
              <p className="text-xs text-gray-400">{formatSize(file.size)}</p>
            </div>
          </div>
          <button
            onClick={() => onRemove(index)}
            className="text-gray-400 hover:text-red-500 transition-colors p-1"
            aria-label="파일 삭제"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </li>
      ))}
    </ul>
  )
}
