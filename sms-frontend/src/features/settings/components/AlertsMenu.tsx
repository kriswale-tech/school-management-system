import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Icon } from '@iconify/react'
import { useAuth } from '@/features/auth/hooks'
import { getSchoolAlerts, SCHOOL_ALERTS_QUERY_KEY } from '../services'

const AlertsMenu = () => {
  const { user } = useAuth()
  const [isOpen, setIsOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement | null>(null)

  const { data: alerts = [] } = useQuery({
    queryKey: [SCHOOL_ALERTS_QUERY_KEY],
    queryFn: getSchoolAlerts,
    enabled: Boolean(user?.school_id),
    staleTime: 60_000,
  })

  useEffect(() => {
    if (!isOpen) return

    const onPointerDown = (event: PointerEvent) => {
      const target = event.target as Node | null
      if (!target || !containerRef.current) return
      if (!containerRef.current.contains(target)) {
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
        className="relative flex items-center justify-center rounded-full bg-slate-100 p-2"
        aria-label="Alerts"
        aria-haspopup="menu"
        aria-expanded={isOpen}
        onClick={() => setIsOpen((open) => !open)}
      >
        <Icon icon="hugeicons:notification-01" className="text-xl" />
        {alerts.length > 0 ? (
          <span className="absolute -right-1 -top-1 flex h-5 min-w-5 items-center justify-center rounded-full bg-red-600 px-1 text-[11px] font-semibold text-white">
            {alerts.length}
          </span>
        ) : null}
      </button>

      {isOpen ? (
        <div
          role="menu"
          className="absolute right-0 z-50 mt-2 w-80 rounded-xl border border-slate-200 bg-white p-2 shadow-lg"
        >
          <p className="px-2 py-1 text-xs font-medium uppercase tracking-wide text-slate-500">
            Alerts
          </p>
          {alerts.length === 0 ? (
            <p className="px-2 py-3 text-sm text-slate-500">No alerts for this term.</p>
          ) : (
            <ul className="space-y-1">
              {alerts.map((alert) => (
                <li key={alert.kind}>
                  <Link
                    to={alert.href}
                    role="menuitem"
                    onClick={() => setIsOpen(false)}
                    className="block rounded-lg px-2 py-2 hover:bg-slate-50"
                  >
                    <span className="block text-sm font-medium text-slate-900">{alert.title}</span>
                    <span className="block text-sm text-slate-500">{alert.summary}</span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}
    </div>
  )
}

export default AlertsMenu
