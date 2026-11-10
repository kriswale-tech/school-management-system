import { NavLink, Navigate, Outlet } from 'react-router-dom'
import { useMessagesAccess } from './permissions'

const TABS: Array<{ to: string; label: string; end?: boolean; capability?: 'profitability' }> = [
  { to: '/messages', label: 'Overview', end: true },
  { to: '/messages/sms-pricing', label: 'SMS pricing' },
  { to: '/messages/email-pricing', label: 'Email pricing' },
  { to: '/messages/providers', label: 'Providers' },
  { to: '/messages/schools', label: 'School usage' },
  { to: '/messages/free-sponsored', label: 'Free & sponsored' },
  { to: '/messages/profitability', label: 'Profitability', capability: 'profitability' },
  { to: '/messages/transactions', label: 'Transactions' },
]

const tabClass = ({ isActive }: { isActive: boolean }) =>
  [
    'whitespace-nowrap rounded-lg px-3 py-1.5 text-sm font-medium transition',
    isActive
      ? 'bg-[var(--color-accent)] text-white'
      : 'text-[var(--color-ink)]/70 hover:bg-white',
  ].join(' ')

export default function MessagesLayout() {
  const { can } = useMessagesAccess()

  if (!can('messages.view')) {
    return <Navigate to="/" replace />
  }

  const tabs = TABS.filter(
    (tab) => tab.capability !== 'profitability' || can('profitability.view'),
  )

  return (
    <div>
      <header className="mb-6">
        <p className="text-sm font-semibold tracking-[0.18em] text-[var(--color-accent)] uppercase">
          Messages
        </p>
        <h1 className="mt-2 font-[family-name:var(--font-display)] text-3xl font-semibold">
          Messaging operations &amp; economics
        </h1>
        <p className="mt-2 max-w-3xl text-sm text-[var(--color-ink)]/70">
          Provider wallets, school credit wallets, cash, and usage economics are tracked as
          separate layers. Every figure below states which layer it belongs to — they are never
          added together.
        </p>
      </header>

      <nav className="mb-6 flex gap-1 overflow-x-auto rounded-xl border border-[var(--color-line)] bg-[var(--color-panel)] p-1">
        {tabs.map((tab) => (
          <NavLink key={tab.to} to={tab.to} end={tab.end} className={tabClass}>
            {tab.label}
          </NavLink>
        ))}
      </nav>

      <Outlet />
    </div>
  )
}
