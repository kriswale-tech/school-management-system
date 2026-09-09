import { lazy } from 'react'
import { Route } from 'react-router-dom'
import { RequireCapability } from '@/features/auth/components/RequireCapability'
import { Capability } from '@/features/auth/capabilities'

const StaffPage = lazy(() => import('./Staff'))
const StaffDetailsPage = lazy(() => import('./pages/StaffDetails'))

export const staffRoutes = (
  <>
    <Route
      path="staff"
      element={
        <RequireCapability capability={Capability.NAV_STAFF}>
          <StaffPage />
        </RequireCapability>
      }
    />
    <Route
      path="staff/:id"
      element={
        <RequireCapability capability={Capability.STAFF_VIEW}>
          <StaffDetailsPage />
        </RequireCapability>
      }
    />
  </>
)
