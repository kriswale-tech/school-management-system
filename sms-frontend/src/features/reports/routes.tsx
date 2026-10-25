import { lazy } from 'react'
import { Route } from 'react-router-dom'
import { RequireCapability } from '@/features/auth/components/RequireCapability'
import { Capability } from '@/features/auth/capabilities'

const ReportsPage = lazy(() => import('./pages/ReportsPage'))

export const reportsRoutes = (
  <Route
    path="reports"
    element={
      <RequireCapability capability={Capability.NAV_REPORTS}>
        <ReportsPage />
      </RequireCapability>
    }
  />
)
