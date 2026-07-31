import { lazy } from 'react'
import { Route } from 'react-router-dom'

const StudentsPage = lazy(() => import('./pages/Students'))

export const studentsRoutes = (
  <>
    <Route path="students" element={<StudentsPage />} />
  </>
)
