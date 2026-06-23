import backgroundImage from '@/assets/images/background.svg'
import { Navigate, Outlet } from 'react-router-dom'
import { AppToaster, AuthLoading } from '@/components/shared'
import { useAuth } from '@/features/auth/hooks'

const AuthLayout = () => {
  const { isReady, isAuthenticated, user } = useAuth()

  if (!isReady) {
    return (
      <>
        <AppToaster />
        <AuthLoading />
      </>
    )
  }

  if (isAuthenticated && user) {
    return <Navigate to={user.school_setup_completed ? '/' : '/setup'} replace />
  }

  return (
    <>
      <AppToaster />
      <div
        className="flex flex-col items-center min-h-screen p-10 py-32 bg-cover bg-center"
        style={{ backgroundImage: `url(${backgroundImage})` }}
      >
        <Outlet />
      </div>
    </>
  )
}

export default AuthLayout
