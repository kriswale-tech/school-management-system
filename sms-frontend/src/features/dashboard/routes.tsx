import { lazy } from 'react'
import { Route } from 'react-router-dom'

const DashboardPage = lazy(() => import('./Dashboard'))

export const dashboardRoutes = (
  <>
    <Route index element={<DashboardPage />} />
    <Route path="dashboard" element={<DashboardPage />} />
  </>
)
