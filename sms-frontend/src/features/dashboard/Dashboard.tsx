import { useAuthStore } from '@/features/auth/store'
import AccountantDashboard from './pages/AccountantDashboard'
import AdminDashboard from './pages/AdminDashboard'
import StaffDashboard from './pages/StaffDashboard'
import TeacherDashboard from './pages/TeacherDashboard'

const Dashboard = () => {
  const role = useAuthStore((state) => state.user?.role)

  if (role === 'admin') {
    return <AdminDashboard />
  }

  if (role === 'teacher') {
    return <TeacherDashboard />
  }

  if (role === 'accountant') {
    return <AccountantDashboard />
  }

  if (role === 'staff') {
    return <StaffDashboard />
  }

  return (
    <div className="rounded-xl bg-white p-6 custom-shadow-md">
      <h1 className="text-lg font-medium text-slate-900">Dashboard</h1>
      <p className="mt-2 text-sm text-slate-500">
        Your role does not have a home screen yet. Use the sidebar to continue.
      </p>
    </div>
  )
}

export default Dashboard
