import { lazy } from 'react'
import { Route } from 'react-router-dom'
import { RequireCapability } from '@/features/auth/components/RequireCapability'
import { Capability } from '@/features/auth/capabilities'

const AssessmentsPage = lazy(() => import('./Assessments'))
const AssessmentSettingsPage = lazy(() => import('./AssessmentSettings'))
const AssessmentDetailPage = lazy(() => import('./AssessmentDetail'))
const AdminAssessmentDetailPage = lazy(() => import('./AdminAssessmentDetail'))
const StudentReportPreviewPage = lazy(() => import('./StudentReportPreview'))

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
      path="assessments/settings"
      element={
        <RequireCapability capability={Capability.ASSESSMENTS_RELEASE}>
          <AssessmentSettingsPage />
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
      path="assessments/classes/:streamId/report/:studentId"
      element={
        <RequireCapability capability={Capability.ASSESSMENTS_RELEASE}>
          <StudentReportPreviewPage />
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
