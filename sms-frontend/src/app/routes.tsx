import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { authRoutes } from '@/features/auth/routes'
import AppLayout from '@/components/layout/AppLayout'
import { setupRoutes } from '@/features/setup/routes'
import { dashboardRoutes } from '@/features/dashboard/routes'
import { studentsRoutes } from '@/features/students/routes'
import { classesRoutes } from '@/features/classes/routes'
import { assessmentsRoutes } from '@/features/assessments/routes'
import { feesRoutes } from '@/features/fees/routes'
import { staffRoutes } from '@/features/staff/routes'
import { reportsRoutes } from '@/features/reports/routes'
import { profileRoutes } from '@/features/profile/routes'
import { settingsRoutes } from '@/features/settings/routes'

const AppRoutes = () => {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<AppLayout />}>
          {dashboardRoutes}
          {studentsRoutes}
          {classesRoutes}
          {assessmentsRoutes}
          {feesRoutes}
          {staffRoutes}
          {reportsRoutes}
          {settingsRoutes}
          {profileRoutes}
        </Route>
        {authRoutes}
        {setupRoutes}
      </Routes>
    </BrowserRouter>
  )
}

export default AppRoutes
