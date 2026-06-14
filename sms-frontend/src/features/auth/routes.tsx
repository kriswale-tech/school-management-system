import { lazy } from 'react'
import { Navigate, Route } from 'react-router-dom'
import { AuthLayout } from '@/components/layout'

const SignupPage = lazy(() => import('./pages/SignupPage'))
const VerifyOTPPage = lazy(() => import('./pages/VerifyOTPPage'))

export const authRoutes = (
  <>
    <Route path="/auth" element={<AuthLayout />}>
      <Route index element={<Navigate to="signup" />} />
      <Route path="signup" element={<SignupPage />} />
      <Route path="signup/verify-otp" element={<VerifyOTPPage />} />
    </Route>
  </>
)
