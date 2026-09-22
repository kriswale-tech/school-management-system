import { Navigate, Outlet } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { useEffect } from 'react'
import { AppToaster, AuthLoading } from '@/components/shared'
import { useAuth } from '@/features/auth/hooks'
import { getUser } from '@/features/auth/services'
import { useAuthStore } from '@/features/auth/store'
import NavBar from '@/components/shared/NavBar'
import SideNav from '../shared/SideNav'

const AppLayout = () => {
  const { isReady, isAuthenticated, user } = useAuth({ requireAuth: true })
  const setUser = useAuthStore((state) => state.setUser)

  const { data: me, isFetched } = useQuery({
    queryKey: ['me', 'session'],
    queryFn: getUser,
    enabled: isReady && isAuthenticated,
    staleTime: 60_000,
  })

  useEffect(() => {
    if (me) setUser(me)
  }, [me, setUser])

  if (!isReady || !isAuthenticated || (isAuthenticated && !isFetched && !user?.capabilities)) {
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
      <div className="flex h-screen overflow-hidden print:block print:h-auto print:overflow-visible">
        <aside className="flex min-h-0 min-w-24 shrink-0 flex-col border-r border-slate-200 bg-white print:hidden">
          <div className="app-shell-header" aria-hidden="true" />
          <div className="min-h-0 flex-1 overflow-hidden">
            <SideNav />
          </div>
        </aside>

        <div className="flex min-w-0 flex-1 flex-col overflow-hidden print:block print:overflow-visible">
          <NavBar />
          <main className="flex-1 overflow-y-auto bg-slate-50 p-6 print:overflow-visible print:bg-white print:p-0">
            <Outlet />
          </main>
        </div>
      </div>
    </>
  )
}

export default AppLayout
