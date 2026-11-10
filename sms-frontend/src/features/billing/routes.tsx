import { Navigate, Route, useLocation } from 'react-router-dom'

function BillingSettingsRedirect() {
  const location = useLocation()
  return <Navigate to={`/settings/billing${location.search}`} replace />
}

export const billingRoutes = (
  <Route path="billing" element={<BillingSettingsRedirect />} />
)
