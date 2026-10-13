import { lazy, type ReactNode } from 'react'
import { Navigate, Outlet, Route } from 'react-router-dom'
import { AuthLoading } from '@/components/shared'
import { useAuth } from '@/features/auth/hooks'

const SettingsPage = lazy(() => import('./pages/SettingsPage'))

const RequireAdmin = ({ children }: { children: ReactNode }) => {
  const { isReady, isAuthenticated, user } = useAuth({ requireAuth: true })

  if (!isReady || !isAuthenticated) {
    return <AuthLoading />
  }

  if (user?.role !== 'admin') {
    return <Navigate to="/dashboard" replace />
  }

  return <>{children}</>
}

export const settingsRoutes = (
  <Route
    path="settings"
    element={
      <RequireAdmin>
        <Outlet />
      </RequireAdmin>
    }
  >
    <Route index element={<Navigate to="school-profile" replace />} />
    <Route path=":tab" element={<SettingsPage />} />
  </Route>
)
