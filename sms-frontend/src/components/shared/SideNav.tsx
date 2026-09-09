import { Icon } from '@iconify/react'
import { NavLink, useLocation } from 'react-router-dom'
import { ConfirmDialog } from '@/components/shared'
import { Capability } from '@/features/auth/capabilities'
import { useCan } from '@/features/auth/hooks/useCan'
import { useLogoutConfirm } from '@/features/auth/hooks'

const navItems = [
  {
    label: 'Dashboard',
    icon: 'hugeicons:dashboard-square-02',
    path: '/dashboard',
    capability: Capability.NAV_DASHBOARD,
  },
  {
    label: 'Students',
    icon: 'hugeicons:student',
    path: '/students',
    capability: Capability.NAV_STUDENTS,
  },
  {
    label: 'Classes',
    icon: 'hugeicons:teacher',
    path: '/classes',
    capability: Capability.NAV_CLASSES,
  },
  {
    label: 'Assessments',
    icon: 'hugeicons:file-chart-column-increasing',
    path: '/assessments',
    capability: Capability.NAV_ASSESSMENTS,
  },
  {
    label: 'Fees',
    icon: 'hugeicons:cash-01',
    path: '/fees',
    capability: Capability.NAV_FEES,
  },
  {
    label: 'Staff',
    icon: 'hugeicons:user-group',
    path: '/staff',
    capability: Capability.NAV_STAFF,
  },
]

const isNavItemActive = (path: string, pathname: string) => {
  if (path === '/dashboard') {
    return pathname === '/' || pathname === '/dashboard'
  }

  return pathname === path || pathname.startsWith(`${path}/`)
}

const SideNav = () => {
  const location = useLocation()
  const { open, isLoading, requestLogout, cancelLogout, confirmLogout } = useLogoutConfirm()
  const canDashboard = useCan(Capability.NAV_DASHBOARD)
  const canStudents = useCan(Capability.NAV_STUDENTS)
  const canClasses = useCan(Capability.NAV_CLASSES)
  const canAssessments = useCan(Capability.NAV_ASSESSMENTS)
  const canFees = useCan(Capability.NAV_FEES)
  const canStaff = useCan(Capability.NAV_STAFF)

  const allowedByCapability: Record<string, boolean> = {
    [Capability.NAV_DASHBOARD]: canDashboard,
    [Capability.NAV_STUDENTS]: canStudents,
    [Capability.NAV_CLASSES]: canClasses,
    [Capability.NAV_ASSESSMENTS]: canAssessments,
    [Capability.NAV_FEES]: canFees,
    [Capability.NAV_STAFF]: canStaff,
  }

  const visibleItems = navItems.filter((item) => allowedByCapability[item.capability])

  return (
    <>
      <nav className="flex h-full min-h-0 flex-col">
      {/* Nav Items */}
      <div className="flex min-h-0 flex-1 flex-col items-center gap-y-4 overflow-y-auto px-2 pt-2">
        {visibleItems.map((item) => {
          const isActive = isNavItemActive(item.path, location.pathname)

          return (
            <NavLink to={item.path} key={item.path} className="group shrink-0">
              <div className="flex flex-col items-center m-auto gap-y-1 ">
                <div
                  className={`rounded-xl size-9 flex items-center justify-center transition-colors duration-150 ${
                    isActive ? 'bg-sky-100' : 'bg-slate-100 group-hover:bg-sky-50'
                  }`}
                >
                  <Icon
                    icon={item.icon}
                    className={`text-xl transition-colors duration-150 ${
                      isActive ? 'text-sky-700' : 'group-hover:text-sky-700'
                    }`}
                  />
                </div>
                <span
                  className={`text-sm transition-colors duration-150 ${
                    isActive ? 'text-sky-700' : 'text-slate-700 group-hover:text-sky-700'
                  }`}
                >
                  {item.label}
                </span>
              </div>
            </NavLink>
          )
        })}
      </div>

      {/* Logout */}
      <div className="flex shrink-0 items-center justify-center px-2 pb-5 pt-2">
        <button type="button" onClick={requestLogout} className="group">
          <div className="flex flex-col items-center m-auto gap-y-1 ">
            <div className="bg-red-100 rounded-xl size-9 flex items-center justify-center transition-colors duration-150 group-hover:bg-red-200">
              <Icon icon="hugeicons:logout-square-01" className="text-xl text-red-600" />
            </div>
            <span className="text-sm text-red-600">Logout</span>
          </div>
        </button>
      </div>
    </nav>

      <ConfirmDialog
        open={open}
        title="Log out?"
        description="You will need to sign in again to continue."
        confirmLabel="Log out"
        cancelLabel="Cancel"
        confirmVariant="danger"
        isLoading={isLoading}
        onConfirm={() => {
          void confirmLogout()
        }}
        onCancel={cancelLogout}
      />
    </>
  )
}

export default SideNav
