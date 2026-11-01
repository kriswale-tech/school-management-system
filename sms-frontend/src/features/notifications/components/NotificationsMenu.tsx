import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Icon } from '@iconify/react'
import { useAuth } from '@/features/auth/hooks'
import {
  getNotifications,
  getNotificationsUnreadCount,
  markAllNotificationsRead,
  markNotificationRead,
  NOTIFICATIONS_QUERY_KEY,
  NOTIFICATIONS_UNREAD_QUERY_KEY,
} from '../services'

const NotificationsMenu = () => {
  const { user } = useAuth()
  const queryClient = useQueryClient()
  const [isOpen, setIsOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement | null>(null)
  const enabled = Boolean(user?.school_id)

  const { data: notificationPage } = useQuery({
    queryKey: [NOTIFICATIONS_QUERY_KEY],
    queryFn: () => getNotifications(false),
    enabled,
    staleTime: 30_000,
  })

  const { data: unreadCount = 0 } = useQuery({
    queryKey: [NOTIFICATIONS_UNREAD_QUERY_KEY],
    queryFn: getNotificationsUnreadCount,
    enabled,
    staleTime: 30_000,
  })

  const notifications = notificationPage?.results ?? []

  const invalidateInbox = () => {
    void queryClient.invalidateQueries({ queryKey: [NOTIFICATIONS_QUERY_KEY] })
    void queryClient.invalidateQueries({ queryKey: [NOTIFICATIONS_UNREAD_QUERY_KEY] })
  }

  const { mutate: markRead } = useMutation({
    mutationFn: markNotificationRead,
    onSuccess: invalidateInbox,
  })

  const { mutate: markAllRead, isPending: markingAll } = useMutation({
    mutationFn: markAllNotificationsRead,
    onSuccess: invalidateInbox,
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
        aria-label="Notifications"
        aria-haspopup="menu"
        aria-expanded={isOpen}
        onClick={() => setIsOpen((open) => !open)}
      >
        <Icon icon="hugeicons:inbox" className="text-xl" />
        {unreadCount > 0 ? (
          <span className="absolute -right-1 -top-1 flex h-5 min-w-5 items-center justify-center rounded-full bg-red-600 px-1 text-[11px] font-semibold text-white">
            {unreadCount}
          </span>
        ) : null}
      </button>

      {isOpen ? (
        <div
          role="menu"
          className="absolute right-0 z-50 mt-2 max-h-[28rem] w-96 overflow-y-auto rounded-xl border border-slate-200 bg-white p-2 shadow-lg"
        >
          <div className="flex items-center justify-between px-2 py-1">
            <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
              Notifications
            </p>
            {unreadCount > 0 ? (
              <button
                type="button"
                className="text-xs font-medium text-slate-600 hover:text-slate-900 disabled:opacity-50"
                disabled={markingAll}
                onClick={() => markAllRead()}
              >
                Mark all as read
              </button>
            ) : null}
          </div>

          {notifications.length === 0 ? (
            <p className="px-2 py-3 text-sm text-slate-500">No notifications yet.</p>
          ) : (
            <ul className="space-y-1">
              {notifications.map((item) => {
                const isUnread = !item.read_at
                return (
                  <li key={item.id}>
                    <Link
                      to={item.href || '#'}
                      role="menuitem"
                      onClick={() => {
                        if (isUnread) {
                          markRead(item.id)
                        }
                        setIsOpen(false)
                      }}
                      className={`block rounded-lg px-2 py-2 hover:bg-slate-50 ${
                        isUnread ? 'bg-slate-50' : ''
                      }`}
                    >
                      <span className="flex items-start justify-between gap-2">
                        <span
                          className={`block text-sm ${
                            isUnread
                              ? 'font-semibold text-slate-900'
                              : 'font-medium text-slate-700'
                          }`}
                        >
                          {item.title}
                        </span>
                        {isUnread ? (
                          <span
                            className="mt-1.5 h-2 w-2 shrink-0 rounded-full bg-red-500"
                            aria-label="Unread"
                          />
                        ) : (
                          <span className="mt-0.5 shrink-0 text-[10px] font-medium uppercase tracking-wide text-slate-400">
                            Read
                          </span>
                        )}
                      </span>
                      <span
                        className={`block text-sm ${
                          isUnread ? 'text-slate-600' : 'text-slate-500'
                        }`}
                      >
                        {item.body}
                      </span>
                    </Link>
                  </li>
                )
              })}
            </ul>
          )}
        </div>
      ) : null}
    </div>
  )
}

export default NotificationsMenu
