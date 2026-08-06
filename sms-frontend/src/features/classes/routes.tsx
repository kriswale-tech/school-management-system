import { lazy } from 'react'
import { Route } from 'react-router-dom'

const ClassesPage = lazy(() => import('./pages/Classes'))
const ClassDetailPage = lazy(() => import('./pages/ClassDetail'))
const ManageClassesPage = lazy(() => import('./manage-classes/ManageClasses'))

export const classesRoutes = (
  <>
    <Route path="classes" element={<ClassesPage />} />
    <Route path="classes/manage" element={<ManageClassesPage />} />
    <Route path="classes/:id" element={<ClassDetailPage />} />
  </>
)
