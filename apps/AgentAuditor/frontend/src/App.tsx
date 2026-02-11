import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState, useEffect } from 'react'
import Navbar from './components/Navbar'
import Dashboard from './pages/Dashboard'
import SubmitAudit from './pages/SubmitAudit'
import AuditExplorer from './pages/AuditExplorer'
import AgentProfile from './pages/AgentProfile'

const queryClient = new QueryClient()

function App() {
  const [darkMode, setDarkMode] = useState(() => {
    const saved = localStorage.getItem('darkMode')
    return saved ? JSON.parse(saved) : false
  })

  useEffect(() => {
    localStorage.setItem('darkMode', JSON.stringify(darkMode))
    if (darkMode) {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
  }, [darkMode])

  const toggleDarkMode = () => setDarkMode(!darkMode)

  return (
    <QueryClientProvider client={queryClient}>
      <Router>
        <div className="min-h-screen bg-slate-50 dark:bg-dark-900 transition-colors duration-200">
          <Navbar darkMode={darkMode} toggleDarkMode={toggleDarkMode} />
          {/* Add pt-16 to account for fixed navbar height */}
          <main className="pt-0">
            <Routes>
              <Route path="/" element={<Dashboard />} />
              <Route path="/submit" element={<SubmitAudit />} />
              <Route path="/audits" element={<AuditExplorer />} />
              <Route path="/agents/:agentId" element={<AgentProfile />} />
            </Routes>
          </main>
        </div>
      </Router>
    </QueryClientProvider>
  )
}

export default App
