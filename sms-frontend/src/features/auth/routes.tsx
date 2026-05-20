import { lazy } from 'react'
import { Navigate, Route } from 'react-router-dom'
import { AuthLayout } from '@/components/layout'

const SignupPage = lazy(() => import('./pages/SignupPage'))

export const authRoutes = (
  <>
    <Route path="/auth" element={<AuthLayout />}>
      <Route index element={<Navigate to="signup" />} />
      <Route path="signup" element={<SignupPage />} />
    </Route>
  </>
)
