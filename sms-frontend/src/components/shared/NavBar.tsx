import { AppLogo } from '.'
import { Icon } from '@iconify/react'
import ProfileComponent from './ProfileComponent'

const NavBar = () => {
  return (
    <nav className="app-shell-header flex shrink-0 items-center justify-between border-b border-slate-200 bg-white px-4">
      {/* logo */}
      <AppLogo widthPx={60} />

      {/* Notification and Profile */}
      <div className="flex items-center ">
        <div className="flex items-center justify-center bg-slate-100 rounded-full p-2">
          <Icon icon="hugeicons:notification-01" className="text-xl" />
        </div>
        <ProfileComponent />
      </div>
    </nav>
  )
}

export default NavBar
