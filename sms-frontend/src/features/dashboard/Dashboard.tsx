import { useAuthStore } from '@/features/auth/store'
import AdminDashboard from './pages/AdminDashboard'

const Dashboard = () => {
  const role = useAuthStore((state) => state.user?.role)

  if (role === 'admin') {
    return <AdminDashboard />
  }

  return (
    <div className="rounded-xl bg-white p-6 custom-shadow-md">
      <h1 className="text-lg font-medium text-slate-900">Dashboard</h1>
      <p className="mt-2 text-sm text-slate-500">
        Your role-specific dashboard is coming soon. Use Classes and Assessments from the sidebar
        for now.
      </p>
    </div>
  )
}

export default Dashboard
