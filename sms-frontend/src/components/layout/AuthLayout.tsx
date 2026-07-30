import backgroundImage from '@/assets/images/background.svg'
import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { AppToaster, AuthLoading } from '@/components/shared'
import { useAuth } from '@/features/auth/hooks'
import { canAccessSchoolSelection, getPostAuthPath } from '@/features/auth/utils'

const AuthLayout = () => {
  const location = useLocation()
  const { isReady, isAuthenticated, user } = useAuth()
  const isSelectSchoolRoute = location.pathname === '/auth/select-school'

  if (!isReady) {
    return (
      <>
        <AppToaster />
        <AuthLoading />
      </>
    )
  }

  if (isAuthenticated && user) {
    if (isSelectSchoolRoute && canAccessSchoolSelection(user)) {
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

    if (user.requires_school_selection) {
      return <Navigate to="/auth/select-school" replace />
    }

    return <Navigate to={getPostAuthPath(user)} replace />
  }

  if (isSelectSchoolRoute) {
    return <Navigate to="/auth/login" replace />
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
