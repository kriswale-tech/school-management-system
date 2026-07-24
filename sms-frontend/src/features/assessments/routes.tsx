import { lazy } from 'react'
import { Route } from 'react-router-dom'

const AssessmentsPage = lazy(() => import('./Assessments'))

export const assessmentsRoutes = (
  <>
    <Route path="assessments" element={<AssessmentsPage />} />
  </>
)
