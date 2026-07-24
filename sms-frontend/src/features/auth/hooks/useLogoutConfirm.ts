import { useState } from 'react'
import { useAuthStore } from '../store'

export function useLogoutConfirm() {
  const logout = useAuthStore((state) => state.logout)
  const [open, setOpen] = useState(false)
  const [isLoading, setIsLoading] = useState(false)

  const requestLogout = () => setOpen(true)
  const cancelLogout = () => setOpen(false)

  const confirmLogout = async () => {
    setIsLoading(true)
    try {
      await logout()
    } finally {
      setIsLoading(false)
      setOpen(false)
    }
  }

  return {
    open,
    isLoading,
    requestLogout,
    cancelLogout,
    confirmLogout,
  }
}
