import { Link, NavLink, Outlet } from 'react-router-dom'
import { useAuthStore } from '@/features/auth/store'
import { useMessagesAccess } from '@/features/messages/permissions'

const navClass = ({ isActive }: { isActive: boolean }) =>
  [
    'rounded-lg px-3 py-2 text-sm font-medium transition',
    isActive
      ? 'bg-[var(--color-accent-soft)] text-[var(--color-accent)]'
      : 'text-[var(--color-ink)]/70 hover:bg-white/70',
  ].join(' ')

export default function AppShell() {
  const user = useAuthStore((s) => s.user)
  const logout = useAuthStore((s) => s.logout)
  const { can } = useMessagesAccess()

  return (
    <div className="min-h-screen">
      <header className="border-b border-[var(--color-line)] bg-white/80 backdrop-blur">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-3 px-6 py-3">
          <div className="flex items-center gap-4">
            <Link
              to="/"
              className="font-[family-name:var(--font-display)] text-sm font-semibold tracking-[0.14em] text-[var(--color-accent)] uppercase"
            >
              SCHOOLASST
            </Link>
            <nav className="flex items-center gap-1">
              <NavLink to="/" end className={navClass}>
                Overview
              </NavLink>
              <NavLink to="/schools" className={navClass}>
                Schools
              </NavLink>
              <NavLink to="/plans" className={navClass}>
                Plans
              </NavLink>
              <NavLink to="/discounts" className={navClass}>
                Discounts
              </NavLink>
              <NavLink to="/payments" className={navClass}>
                Payments
              </NavLink>
              {can('messages.view') && (
                <NavLink to="/messages" className={navClass}>
                  Messages
                </NavLink>
              )}
              <NavLink to="/settings" className={navClass}>
                Settings
              </NavLink>
            </nav>
          </div>
          <div className="flex items-center gap-3 text-sm">
            <span className="text-[var(--color-ink)]/70">{user?.email}</span>
            <button
              type="button"
              onClick={() => logout()}
              className="rounded-lg border border-[var(--color-line)] px-3 py-1.5"
            >
              Sign out
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto w-full max-w-7xl px-6 py-10">
        <Outlet />
      </main>
    </div>
  )
}
