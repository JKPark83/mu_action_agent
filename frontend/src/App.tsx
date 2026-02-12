import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import Home from './pages/Home'
import AnalysisProgress from './pages/AnalysisProgress'
import Report from './pages/Report'
import History from './pages/History'

const queryClient = new QueryClient()

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/analysis/:id" element={<AnalysisProgress />} />
          <Route path="/report/:id" element={<Report />} />
          <Route path="/history" element={<History />} />
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}

export default App
