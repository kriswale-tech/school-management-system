import type { NavigateFunction } from 'react-router-dom'
import type { User } from '@/features/auth/types'
import type { SetupProgressResponse } from '../types'

type HandleSetupProgressOptions = {
  navigate: NavigateFunction
  user: User | null
  // eslint-disable-next-line no-unused-vars
  setUser: (user: User) => void
}

export function handleSetupProgressResponse(
  response: SetupProgressResponse,
  { navigate, user, setUser }: HandleSetupProgressOptions,
) {
  if (response.is_complete) {
    if (user) {
      setUser({ ...user, school_setup_completed: true })
    }
    navigate('/')
    return
  }

  navigate(`/setup/${response.next_step}`)
}
