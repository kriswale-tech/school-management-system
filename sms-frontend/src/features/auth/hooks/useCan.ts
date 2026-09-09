import { useAuthStore } from '@/features/auth/store'
import type { CapabilityCode } from '@/features/auth/capabilities'
import type { AccessInfo } from '@/features/auth/types'

const EMPTY_ACCESS: AccessInfo = {
  mode: 'school',
  is_class_teacher: false,
  is_subject_teacher: false,
}

/** Whether the current session includes the given capability. */
export function useCan(capability: CapabilityCode | string): boolean {
  const capabilities = useAuthStore((state) => state.user?.capabilities)
  return Boolean(capabilities?.includes(capability))
}

export function useCanAny(capabilities: Array<CapabilityCode | string>): boolean {
  const userCaps = useAuthStore((state) => state.user?.capabilities)
  if (!userCaps?.length) return false
  return capabilities.some((cap) => userCaps.includes(cap))
}

export function useAccess(): AccessInfo {
  return useAuthStore((state) => state.user?.access) ?? EMPTY_ACCESS
}
