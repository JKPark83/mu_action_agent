import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Header from './components/common/Header'
import Home from './pages/Home'
import AnalysisProgress from './pages/AnalysisProgress'
import Report from './pages/Report'
import History from './pages/History'

const queryClient = new QueryClient()

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="min-h-screen bg-gray-50">
          <Header />
          <main>
            <Routes>
              <Route path="/" element={<Home />} />
              <Route path="/analysis/:id" element={<AnalysisProgress />} />
              <Route path="/report/:id" element={<Report />} />
              <Route path="/history" element={<History />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
