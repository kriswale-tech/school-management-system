import { lazy } from 'react'
import { Route } from 'react-router-dom'

const StaffPage = lazy(() => import('./Staff'))
const StaffDetailsPage = lazy(() => import('./pages/StaffDetails'))

export const staffRoutes = (
  <>
    <Route path="staff" element={<StaffPage />} />
    <Route path="staff/:id" element={<StaffDetailsPage />} />
  </>
)
