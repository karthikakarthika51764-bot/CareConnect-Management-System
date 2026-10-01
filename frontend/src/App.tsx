import { useEffect, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from './components/AppShell'
import { apiGet, clearSession, getSession } from './services/api'
import type { User } from './types'
import { AuthPage } from './pages/AuthPage'
import { BusinessSettingsPage } from './pages/BusinessSettingsPage'
import { CallDetailsPage } from './pages/CallDetailsPage'
import { DashboardPage } from './pages/DashboardPage'
import { AssistantPage } from './pages/AssistantPage'
import { WorkspacePage } from './pages/WorkspacePage'

function App() {
  const [authenticated, setAuthenticated] = useState(() => Boolean(getSession()))
  const queryClient = useQueryClient()
  const profile = useQuery({
    queryKey: ['current-user'],
    queryFn: () => apiGet<User>('/api/v1/auth/me'),
    enabled: authenticated,
    retry: false,
  })

  useEffect(() => {
    const handleSessionChange = () => {
      setAuthenticated(Boolean(getSession()))
      void queryClient.invalidateQueries({ queryKey: ['current-user'] })
    }
    window.addEventListener('careconnect:session', handleSessionChange)
    return () => window.removeEventListener('careconnect:session', handleSessionChange)
  }, [queryClient])

  useEffect(() => {
    if (profile.isError && authenticated) clearSession()
  }, [profile.isError, authenticated])

  if (!authenticated) return <AuthPage />
  if (profile.isLoading || !profile.data) return <main className="app-loading"><span className="brand-mark"><span /></span><p>Opening your clinic workspace…</p></main>

  return <Routes>
    <Route element={<AppShell user={profile.data} />}>
      <Route index element={<DashboardPage />} />
      <Route path="calls" element={<WorkspacePage />} />
      <Route path="calls/:id" element={<CallDetailsPage />} />
      <Route path="appointments" element={<WorkspacePage />} />
      <Route path="customers" element={<WorkspacePage />} />
      <Route path="leads" element={<WorkspacePage />} />
      <Route path="follow-ups" element={<WorkspacePage />} />
      <Route path="doctors" element={<WorkspacePage />} />
      <Route path="services" element={<WorkspacePage />} />
      <Route path="knowledge" element={<WorkspacePage />} />
      <Route path="assistant" element={<AssistantPage />} />
      <Route path="escalations" element={<WorkspacePage />} />
      <Route path="analytics" element={<WorkspacePage />} />
      <Route path="staff" element={<WorkspacePage />} />
      <Route path="settings" element={<BusinessSettingsPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Route>
  </Routes>
}

export default App
