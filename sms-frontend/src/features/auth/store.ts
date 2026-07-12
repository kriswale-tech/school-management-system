import { create } from 'zustand'
import { createJSONStorage, persist } from 'zustand/middleware'
import type { User } from './types'

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  verificationPhone: string | null
  setVerificationPhone: (_phoneNumber: string) => void
  clearVerificationPhone: () => void
  setUser: (_user: User) => void
  logout: () => Promise<void>
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,
      verificationPhone: null,
      setVerificationPhone: (phoneNumber) => set({ verificationPhone: phoneNumber }),
      clearVerificationPhone: () => set({ verificationPhone: null }),
      setUser: (user) => set({ user, isAuthenticated: true }),
      logout: async () => {
        try {
          const { logout: logoutRequest } = await import('@/features/auth/services')
          await logoutRequest()
        } catch {
          // session may already be expired
        } finally {
          set({ user: null, isAuthenticated: false, verificationPhone: null })
          window.location.assign('/auth/login')
        }
      },
    }),
    {
      name: 'auth-store',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
        verificationPhone: state.verificationPhone,
      }),
    },
  ),
)
