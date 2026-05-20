import backgroundImage from '@/assets/images/background.svg'
import { Outlet } from 'react-router-dom'

const AuthLayout = () => {
  return (
    <div
      className="flex flex-col items-center  min-h-screen p-10 py-32 bg-cover bg-center"
      style={{ backgroundImage: `url(${backgroundImage})` }}
    >
      <Outlet />
    </div>
  )
}

export default AuthLayout
