import { lazy } from 'react'
import { Route } from 'react-router-dom'

const FeesPage = lazy(() => import('./pages/Fees'))
const FeeSettingsPage = lazy(() => import('./pages/FeeSettings'))
const FeeDetailPage = lazy(() => import('./pages/FeeDetail'))

export const feesRoutes = (
  <>
    <Route path="fees" element={<FeesPage />} />
    <Route path="fees/settings" element={<FeeSettingsPage />} />
    <Route path="fees/:studentId" element={<FeeDetailPage />} />
  </>
)
