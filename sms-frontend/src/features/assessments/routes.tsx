import { lazy } from 'react'
import { Route } from 'react-router-dom'
import { RequireCapability } from '@/features/auth/components/RequireCapability'
import { Capability } from '@/features/auth/capabilities'

const AssessmentsPage = lazy(() => import('./Assessments'))

export const assessmentsRoutes = (
  <>
    <Route
      path="assessments"
      element={
        <RequireCapability capability={Capability.NAV_ASSESSMENTS}>
          <AssessmentsPage />
        </RequireCapability>
      }
    />
  </>
)
