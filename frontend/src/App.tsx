import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Header from './components/common/Header'
import Dashboard from './pages/Dashboard'
import NewAnalysis from './pages/NewAnalysis'
import AnalysisProgress from './pages/AnalysisProgress'
import Report from './pages/Report'

const queryClient = new QueryClient()

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="min-h-screen bg-gray-50">
          <Header />
          <main>
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/new" element={<NewAnalysis />} />
              <Route path="/analysis/:id" element={<AnalysisProgress />} />
              <Route path="/report/:id" element={<Report />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
