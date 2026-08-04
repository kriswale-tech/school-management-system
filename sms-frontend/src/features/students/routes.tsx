import { lazy } from 'react'
import { Route } from 'react-router-dom'

const StudentsPage = lazy(() => import('./pages/Students'))
const StudentDetailsPage = lazy(() => import('./pages/StudentDetails'))

export const studentsRoutes = (
  <>
    <Route path="students" element={<StudentsPage />} />
    <Route path="students/:id" element={<StudentDetailsPage />} />
  </>
)
