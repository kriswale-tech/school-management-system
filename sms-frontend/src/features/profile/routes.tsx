import { lazy } from 'react'
import { Route } from 'react-router-dom'

const ProfilePage = lazy(() => import('./pages/ProfilePage'))

export const profileRoutes = <Route path="profile" element={<ProfilePage />} />
