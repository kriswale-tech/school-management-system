import { Navigate, Outlet } from 'react-router-dom'
import { AppToaster, AuthLoading } from '@/components/shared'
import { useAuth } from '@/features/auth/hooks'
import NavBar from '@/components/shared/NavBar'
import SideNav from '../shared/SideNav'

const AppLayout = () => {
  const { isReady, isAuthenticated, user } = useAuth({ requireAuth: true })

  if (!isReady || !isAuthenticated) {
    return (
      <>
        <AppToaster />
        <AuthLoading />
      </>
    )
  }

  if (user?.requires_school_selection) {
    return <Navigate to="/auth/select-school" replace />
  }

  if (user && !user.school_setup_completed) {
    return <Navigate to="/setup" replace />
  }

  return (
    <>
      <AppToaster />
      <div className="flex h-screen overflow-hidden">
        <aside className="flex min-h-0 min-w-24 shrink-0 flex-col border-r border-slate-200 bg-white">
          <div className="app-shell-header" aria-hidden="true" />
          <div className="min-h-0 flex-1 overflow-hidden">
            <SideNav />
          </div>
        </aside>

        <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
          <NavBar />
          <main className="flex-1 overflow-y-auto bg-slate-50 p-6">
            <Outlet />
          </main>
        </div>
      </div>
    </>
  )
}

export default AppLayout
