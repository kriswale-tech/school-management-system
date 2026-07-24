import { lazy } from 'react'
import { Route } from 'react-router-dom'

const ClassesPage = lazy(() => import('./Classes'))

export const classesRoutes = (
  <>
    <Route path="classes" element={<ClassesPage />} />
  </>
)
