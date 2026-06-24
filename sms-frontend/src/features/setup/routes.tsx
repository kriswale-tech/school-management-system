import { lazy } from 'react'
import { Route } from 'react-router-dom'
import SetupLayout from '@/components/layout/SetupLayout'

const SetupStepPage = lazy(() => import('./pages/SetupStepPage'))

export const setupRoutes = (
  <>
    <Route path="/setup" element={<SetupLayout />}>
      <Route path=":step" element={<SetupStepPage />} />
    </Route>
  </>
)
