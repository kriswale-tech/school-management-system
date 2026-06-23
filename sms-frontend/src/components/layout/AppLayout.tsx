import { Navigate, Outlet } from 'react-router-dom'
import { AppToaster, AuthLoading } from '@/components/shared'
import { useAuth } from '@/features/auth/hooks'

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

  if (user && !user.school_setup_completed) {
    return <Navigate to="/setup" replace />
  }

  return (
    <>
      <AppToaster />
      <div>
        <Outlet />
      </div>
    </>
  )
}

export default AppLayout
