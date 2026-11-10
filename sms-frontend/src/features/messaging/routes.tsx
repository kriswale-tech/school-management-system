import { Navigate, Route, useLocation } from 'react-router-dom'

function MessagingSettingsRedirect() {
  const location = useLocation()
  return <Navigate to={`/settings/messaging${location.search}`} replace />
}

export const messagingRoutes = (
  <Route path="messaging" element={<MessagingSettingsRedirect />} />
)
