const SORT_OPTIONS = [
  { label: '최신순', value: 'created_at:desc' },
  { label: '수익률 높은순', value: 'expected_roi:desc' },
  { label: '수익률 낮은순', value: 'expected_roi:asc' },
  { label: '감정가 높은순', value: 'appraised_value:desc' },
  { label: '추천순', value: 'recommendation:asc' },
] as const

interface SortDropdownProps {
  value: string
  onChange: (value: string) => void
}

export default function SortDropdown({ value, onChange }: SortDropdownProps) {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      className="text-sm border border-gray-300 rounded-lg px-3 py-2 bg-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
    >
      {SORT_OPTIONS.map((option) => (
        <option key={option.value} value={option.value}>
          {option.label}
        </option>
      ))}
    </select>
  )
}
