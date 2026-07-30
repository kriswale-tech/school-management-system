import type { User } from './types'

/** Destination after auth once a school is scoped (or selection is not required). */
export function getPostAuthPath(user: Pick<User, 'school_setup_completed'>): string {
  return user.school_setup_completed ? '/' : '/setup'
}

/** Whether the user may open the school picker (must choose, or switch among several). */
export function canAccessSchoolSelection(
  user: Pick<User, 'requires_school_selection' | 'schools'> | null | undefined,
): boolean {
  if (!user) return false
  return user.requires_school_selection || (user.schools?.length ?? 0) > 1
}
