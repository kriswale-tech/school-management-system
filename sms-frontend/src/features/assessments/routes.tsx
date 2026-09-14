import { lazy } from 'react'
import { Route } from 'react-router-dom'
import { RequireCapability } from '@/features/auth/components/RequireCapability'
import { Capability } from '@/features/auth/capabilities'

const AssessmentsPage = lazy(() => import('./Assessments'))
const AssessmentDetailPage = lazy(() => import('./AssessmentDetail'))
const AdminAssessmentDetailPage = lazy(() => import('./AdminAssessmentDetail'))

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
    <Route
      path="assessments/classes/:streamId"
      element={
        <RequireCapability capability={Capability.ASSESSMENTS_RELEASE}>
          <AdminAssessmentDetailPage />
        </RequireCapability>
      }
    />
    <Route
      path="assessments/:classTeacherId"
      element={
        <RequireCapability capability={Capability.NAV_ASSESSMENTS}>
          <AssessmentDetailPage />
        </RequireCapability>
      }
    />
  </>
)
