import { lazy } from 'react'
import { Route } from 'react-router-dom'

const FeesPage = lazy(() => import('./Fees'))

export const feesRoutes = (
  <>
    <Route path="fees" element={<FeesPage />} />
  </>
)
