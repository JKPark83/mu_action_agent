export function LoadingSkeleton() {
  return (
    <div className="animate-pulse space-y-4 p-8">
      <div className="h-8 bg-gray-200 rounded w-1/3" />
      <div className="h-4 bg-gray-200 rounded w-2/3" />
      <div className="h-4 bg-gray-200 rounded w-1/2" />
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-6">
        <div className="h-32 bg-gray-200 rounded" />
        <div className="h-32 bg-gray-200 rounded" />
      </div>
      <div className="h-48 bg-gray-200 rounded mt-4" />
    </div>
  )
}

export function Spinner({ className = '' }: { className?: string }) {
  return (
    <svg
      className={`animate-spin h-5 w-5 text-blue-600 ${className}`}
      xmlns="http://www.w3.org/2000/svg"
      fill="none"
      viewBox="0 0 24 24"
    >
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
      />
    </svg>
  )
}

export function ErrorMessage({ message = '오류가 발생했습니다.' }: { message?: string }) {
  return (
    <div className="flex flex-col items-center justify-center p-12 text-center">
      <div className="w-12 h-12 rounded-full bg-red-100 flex items-center justify-center mb-4">
        <span className="text-red-600 text-xl font-bold">!</span>
      </div>
      <p className="text-gray-600">{message}</p>
    </div>
  )
}
