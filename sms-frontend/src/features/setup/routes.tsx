import { lazy } from 'react'
import { Navigate, Route } from 'react-router-dom'
import SetupLayout from '@/components/layout/SetupLayout'

const SchoolProfile = lazy(() => import('./pages/SchoolProfile'))

export const setupRoutes = (
  <>
    <Route path="/setup" element={<SetupLayout />}>
      <Route index element={<Navigate to="school-profile" />} />
      <Route path="school-profile" element={<SchoolProfile />} />
    </Route>
  </>
)
