import { Navigate } from 'react-router-dom'
import type { ReactNode } from 'react'
import { useCan } from '@/features/auth/hooks/useCan'
import type { CapabilityCode } from '@/features/auth/capabilities'
import { AuthLoading } from '@/components/shared'
import { useAuth } from '@/features/auth/hooks'

type RequireCapabilityProps = {
  capability: CapabilityCode | string
  children: ReactNode
  /** Where to send users who lack the capability. */
  fallbackTo?: string
}

/** Route guard: require auth + a capability from /me. */
export function RequireCapability({
  capability,
  children,
  fallbackTo = '/dashboard',
}: RequireCapabilityProps) {
  const { isReady, isAuthenticated } = useAuth({ requireAuth: true })
  const allowed = useCan(capability)

  if (!isReady || !isAuthenticated) {
    return <AuthLoading />
  }

  if (!allowed) {
    return <Navigate to={fallbackTo} replace />
  }

  return <>{children}</>
}
