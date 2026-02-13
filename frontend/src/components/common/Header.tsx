import { Link, useLocation } from 'react-router-dom'

const NAV_ITEMS = [
  { to: '/', label: '대시보드' },
  { to: '/new', label: '새 분석', isPrimary: true },
] as const

export default function Header() {
  const location = useLocation()

  return (
    <header className="bg-white border-b border-gray-200">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          <Link to="/" className="flex items-center gap-2">
            <span className="text-xl font-bold text-blue-600">AuctionAI</span>
            <span className="text-sm text-gray-500 hidden sm:inline">부동산 경매 분석</span>
          </Link>
          <nav className="flex gap-4 items-center">
            {NAV_ITEMS.map(({ to, label, ...rest }) => {
              const isPrimary = 'isPrimary' in rest && rest.isPrimary
              if (isPrimary) {
                return (
                  <Link
                    key={to}
                    to={to}
                    className="text-sm font-medium bg-blue-600 text-white hover:bg-blue-700 rounded-md px-4 py-2 transition-colors"
                  >
                    {label}
                  </Link>
                )
              }
              return (
                <Link
                  key={to}
                  to={to}
                  className={`text-sm font-medium px-3 py-2 rounded-md transition-colors ${
                    location.pathname === to
                      ? 'text-blue-600 bg-blue-50'
                      : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                  }`}
                >
                  {label}
                </Link>
              )
            })}
          </nav>
        </div>
      </div>
    </header>
  )
}
