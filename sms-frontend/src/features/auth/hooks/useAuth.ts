import { useEffect, useState } from 'react'
import { useAuthStore } from '@/features/auth/store'

type UseAuthOptions = {
  /** Redirect unauthenticated users via store logout */
  requireAuth?: boolean
}

export function useAuth(options: UseAuthOptions = {}) {
  const { requireAuth = false } = options
  const isAuthenticated = useAuthStore((state) => state.isAuthenticated)
  const user = useAuthStore((state) => state.user)
  const logout = useAuthStore((state) => state.logout)
  const [isReady, setIsReady] = useState(useAuthStore.persist.hasHydrated())

  useEffect(() => {
    return useAuthStore.persist.onFinishHydration(() => {
      setIsReady(true)
    })
  }, [])

  useEffect(() => {
    if (!requireAuth || !isReady || isAuthenticated) return

    void logout()
  }, [requireAuth, isReady, isAuthenticated, logout])

  return {
    isReady,
    isAuthenticated: isReady && isAuthenticated,
    user: isReady ? user : null,
    logout,
  }
}
