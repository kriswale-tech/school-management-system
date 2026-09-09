import { lazy } from 'react'
import { Route } from 'react-router-dom'
import { RequireCapability } from '@/features/auth/components/RequireCapability'
import { Capability } from '@/features/auth/capabilities'

const ClassesPage = lazy(() => import('./pages/Classes'))
const ClassDetailPage = lazy(() => import('./pages/ClassDetail'))
const SubjectDetailPage = lazy(() => import('./pages/SubjectDetail'))
const ManageClassesPage = lazy(() => import('./manage-classes/ManageClasses'))

export const classesRoutes = (
  <>
    <Route
      path="classes"
      element={
        <RequireCapability capability={Capability.NAV_CLASSES}>
          <ClassesPage />
        </RequireCapability>
      }
    />
    <Route
      path="classes/manage"
      element={
        <RequireCapability capability={Capability.CLASSES_MANAGE}>
          <ManageClassesPage />
        </RequireCapability>
      }
    />
    <Route
      path="classes/subjects/:assignmentId"
      element={
        <RequireCapability capability={Capability.CLASSES_VIEW}>
          <SubjectDetailPage />
        </RequireCapability>
      }
    />
    <Route
      path="classes/:id"
      element={
        <RequireCapability capability={Capability.CLASSES_VIEW}>
          <ClassDetailPage />
        </RequireCapability>
      }
    />
  </>
)
