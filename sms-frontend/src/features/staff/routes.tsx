import { lazy } from 'react'
import { Route } from 'react-router-dom'

const StaffPage = lazy(() => import('./Staff'))

export const staffRoutes = (
  <>
    <Route path="staff" element={<StaffPage />} />
  </>
)
