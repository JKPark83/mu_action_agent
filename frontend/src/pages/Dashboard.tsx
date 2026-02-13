import { useState, useEffect, useMemo, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { useAnalysisList, useToggleFavorite } from '../hooks/useAnalysis'
import { deleteAnalysis } from '../api/client'
import type { AnalysisListParams } from '../types'
import AnalysisCard from '../components/dashboard/AnalysisCard'
import SearchBar from '../components/dashboard/SearchBar'
import SortDropdown from '../components/dashboard/SortDropdown'
import { LoadingSkeleton, ErrorMessage } from '../components/common/Loading'

export default function Dashboard() {
  const [searchInput, setSearchInput] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [sortValue, setSortValue] = useState('created_at:desc')
  const [favoritesOnly, setFavoritesOnly] = useState(false)
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)

  // Debounce search input
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedSearch(searchInput), 300)
    return () => clearTimeout(timer)
  }, [searchInput])

  const params = useMemo<AnalysisListParams>(() => {
    const [sort_by, sort_order] = sortValue.split(':') as [
      AnalysisListParams['sort_by'],
      AnalysisListParams['sort_order'],
    ]
    return {
      ...(debouncedSearch ? { search: debouncedSearch } : {}),
      sort_by,
      sort_order,
      ...(favoritesOnly ? { favorites_only: true } : {}),
    }
  }, [debouncedSearch, sortValue, favoritesOnly])

  const { data: analyses, isLoading, isError, refetch } = useAnalysisList(params)
  const { mutate: toggleFavorite } = useToggleFavorite()

  const handleDelete = useCallback(async (id: string) => {
    if (deleteConfirm === id) {
      await deleteAnalysis(id)
      setDeleteConfirm(null)
      refetch()
    } else {
      setDeleteConfirm(id)
      setTimeout(() => setDeleteConfirm(null), 3000)
    }
  }, [deleteConfirm, refetch])

  if (isLoading) return <LoadingSkeleton />
  if (isError) return <ErrorMessage message="분석 목록을 불러오는 중 오류가 발생했습니다." />

  return (
    <div className="max-w-6xl mx-auto py-8 px-4 sm:px-6 lg:px-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">내 분석 리포트</h1>

      {/* Filter bar */}
      <div className="flex flex-col sm:flex-row gap-3 mb-6">
        <div className="flex-1">
          <SearchBar value={searchInput} onChange={setSearchInput} />
        </div>
        <div className="flex gap-3">
          <SortDropdown value={sortValue} onChange={setSortValue} />
          <button
            onClick={() => setFavoritesOnly((prev) => !prev)}
            className={`flex items-center gap-1.5 px-3 py-2 text-sm rounded-lg border transition-colors ${
              favoritesOnly
                ? 'bg-yellow-100 text-yellow-800 border-yellow-300'
                : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-50'
            }`}
          >
            {favoritesOnly ? (
              <svg className="w-4 h-4 text-yellow-500" fill="currentColor" viewBox="0 0 20 20">
                <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
              </svg>
            ) : (
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M11.48 3.499a.562.562 0 011.04 0l2.125 5.111a.563.563 0 00.475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602a.563.563 0 00-.182.557l1.285 5.385a.562.562 0 01-.84.61l-4.725-2.885a.563.563 0 00-.586 0L6.982 20.54a.562.562 0 01-.84-.61l1.285-5.386a.562.562 0 00-.182-.557l-4.204-3.602a.563.563 0 01.321-.988l5.518-.442a.563.563 0 00.475-.345L11.48 3.5z" />
              </svg>
            )}
            즐겨찾기
          </button>
        </div>
      </div>

      {/* Card grid or empty state */}
      {analyses && analyses.length > 0 ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {analyses.map((analysis) => (
            <AnalysisCard
              key={analysis.id}
              analysis={analysis}
              onToggleFavorite={toggleFavorite}
              onDelete={handleDelete}
              isDeleteConfirm={deleteConfirm === analysis.id}
            />
          ))}
        </div>
      ) : (
        <div className="flex flex-col items-center justify-center py-16 text-center">
          <div className="w-16 h-16 rounded-full bg-gray-100 flex items-center justify-center mb-4">
            <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z" />
            </svg>
          </div>
          <p className="text-gray-500 mb-4">아직 분석 이력이 없습니다.</p>
          <Link
            to="/new"
            className="text-sm font-medium text-blue-600 hover:text-blue-700"
          >
            새 분석 시작하기
          </Link>
        </div>
      )}
    </div>
  )
}
