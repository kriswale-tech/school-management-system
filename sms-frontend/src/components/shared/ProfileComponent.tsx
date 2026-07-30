import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Icon } from '@iconify/react'
import AvatarComponent from '@/components/ui/AvatarComponent'
import { ConfirmDialog } from '@/components/shared'
import { useAuth, useLogoutConfirm } from '@/features/auth/hooks'
import { mergeClasses } from '@/utils'

const ProfileComponent = () => {
  const { user } = useAuth()
  const { open, isLoading, requestLogout, cancelLogout, confirmLogout } = useLogoutConfirm()
  const [isOpen, setIsOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    if (!isOpen) return

    const onPointerDown = (event: PointerEvent) => {
      const target = event.target as Node | null
      if (!target) return
      if (containerRef.current && !containerRef.current.contains(target)) {
        setIsOpen(false)
      }
    }

    window.addEventListener('pointerdown', onPointerDown)
    return () => window.removeEventListener('pointerdown', onPointerDown)
  }, [isOpen])

  return (
    <div ref={containerRef} className="relative">
      <button
        type="button"
        onClick={() => setIsOpen((open) => !open)}
        className="flex items-center gap-2 rounded-full px-2 py-1"
        aria-haspopup="menu"
        aria-expanded={isOpen}
      >
        <AvatarComponent
          image={user?.profile?.profile_picture}
          fullName={user?.full_name}
          size={34}
        />
        <div className="hidden sm:block text-left">
          <p className="text-sm font-medium text-slate-900 leading-tight">
            {user?.full_name ?? ''}
          </p>
        </div>
        <Icon
          icon="mdi:chevron-down"
          className={mergeClasses('text-slate-600 transition-transform', isOpen && 'rotate-180')}
        />
      </button>

      {isOpen ? (
        <div
          role="menu"
          className="absolute right-0 mt-2 w-56 rounded-xl border border-slate-200 bg-white shadow-lg p-1"
        >
          <div className="px-3 py-2">
            <p className="text-xs text-slate-500">Role</p>
            <p className="text-sm font-medium text-slate-900 capitalize">
              {user?.role?.replace(/_/g, ' ') ?? '-'}
            </p>
          </div>
          <div className="my-1 h-px bg-slate-100" />
          {(user?.schools?.length ?? 0) > 1 ? (
            <Link
              to="/auth/select-school"
              role="menuitem"
              onClick={() => setIsOpen(false)}
              className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-slate-700 hover:bg-slate-100"
            >
              <Icon icon="hugeicons:school" className="text-lg" />
              Switch school
            </Link>
          ) : null}
          <Link
            to="/profile"
            role="menuitem"
            onClick={() => setIsOpen(false)}
            className="flex items-center gap-2 rounded-lg px-3 py-2 text-sm text-slate-700 hover:bg-slate-100"
          >
            <Icon icon="hugeicons:user" className="text-lg" />
            Profile
          </Link>
          <button
            type="button"
            role="menuitem"
            onClick={() => {
              setIsOpen(false)
              requestLogout()
            }}
            className="flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-sm text-red-600 hover:bg-red-50"
          >
            <Icon icon="hugeicons:logout-square-01" className="text-lg" />
            Logout
          </button>
        </div>
      ) : null}

      <ConfirmDialog
        open={open}
        title="Logout"
        message="Are you sure you want to logout?"
        confirmLabel="Logout"
        onClose={cancelLogout}
        onConfirm={() => void confirmLogout()}
        isLoading={isLoading}
      />
    </div>
  )
}

export default ProfileComponent
