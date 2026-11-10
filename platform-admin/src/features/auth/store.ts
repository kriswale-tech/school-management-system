import { create } from 'zustand'
import type { PlatformUser } from './types'
import * as authApi from './services'

type AuthState = {
  user: PlatformUser | null
  bootstrapped: boolean
  setUser: (user: PlatformUser | null) => void
  bootstrap: () => Promise<void>
  logout: () => Promise<void>
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  bootstrapped: false,
  setUser: (user) => set({ user }),
  bootstrap: async () => {
    try {
      const user = await authApi.fetchMe()
      set({ user, bootstrapped: true })
    } catch {
      set({ user: null, bootstrapped: true })
    }
  },
  logout: async () => {
    try {
      await authApi.logout()
    } finally {
      set({ user: null })
    }
  },
}))
