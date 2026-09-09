import { lazy } from 'react'
import { Route } from 'react-router-dom'
import { RequireCapability } from '@/features/auth/components/RequireCapability'
import { Capability } from '@/features/auth/capabilities'

const StudentsPage = lazy(() => import('./pages/Students'))
const StudentDetailsPage = lazy(() => import('./pages/StudentDetails'))

export const studentsRoutes = (
  <>
    <Route
      path="students"
      element={
        <RequireCapability capability={Capability.NAV_STUDENTS}>
          <StudentsPage />
        </RequireCapability>
      }
    />
    <Route
      path="students/:id"
      element={
        <RequireCapability capability={Capability.STUDENTS_VIEW}>
          <StudentDetailsPage />
        </RequireCapability>
      }
    />
  </>
)
