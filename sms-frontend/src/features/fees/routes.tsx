import { lazy } from 'react'
import { Route } from 'react-router-dom'
import { RequireCapability } from '@/features/auth/components/RequireCapability'
import { Capability } from '@/features/auth/capabilities'

const FeesPage = lazy(() => import('./pages/Fees'))
const FeeSettingsPage = lazy(() => import('./pages/FeeSettings'))
const FeeDetailPage = lazy(() => import('./pages/FeeDetail'))

export const feesRoutes = (
  <>
    <Route
      path="fees"
      element={
        <RequireCapability capability={Capability.NAV_FEES}>
          <FeesPage />
        </RequireCapability>
      }
    />
    <Route
      path="fees/settings"
      element={
        <RequireCapability capability={Capability.FEES_MANAGE_SETTINGS}>
          <FeeSettingsPage />
        </RequireCapability>
      }
    />
    <Route
      path="fees/:studentId"
      element={
        <RequireCapability capability={Capability.FEES_VIEW}>
          <FeeDetailPage />
        </RequireCapability>
      }
    />
  </>
)
