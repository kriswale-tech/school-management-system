import { Outlet } from 'react-router-dom'
import { AppToaster, AuthLoading } from '@/components/shared'
import { useAuth } from '@/features/auth/hooks'

const AppLayout = () => {
  const { isReady, isAuthenticated } = useAuth({ requireAuth: true })

  if (!isReady || !isAuthenticated) {
    return (
      <>
        <AppToaster />
        <AuthLoading />
      </>
    )
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
