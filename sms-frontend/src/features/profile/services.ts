import api from '@/app/api/api'
import type { User } from '@/features/auth/types'

export const updateMyProfile = async (payload: FormData) => {
  const response = await api.patch<User>('/accounts/me/', payload)
  return response.data
}
