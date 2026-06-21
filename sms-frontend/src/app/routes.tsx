import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { authRoutes } from '@/features/auth/routes'
import AppLayout from '@/components/layout/AppLayout'
import { lazy } from 'react'

const DashboardPage = lazy(() => import('@/features/dashboard/Dashboard'))

const AppRoutes = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<AppLayout />}>
          <Route index element={<DashboardPage />} />
        </Route>
        {authRoutes}
      </Routes>
    </BrowserRouter>
  )
}

export default AppRoutes
