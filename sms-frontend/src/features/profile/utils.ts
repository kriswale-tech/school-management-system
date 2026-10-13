import dayjs from '@/lib/dayjs'
import type { User } from '@/features/auth/types'
import type { ProfileFormData } from './types'

const PROFILE_FORM_FIELDS: (keyof ProfileFormData)[] = [
  'first_name',
  'last_name',
  'email',
  'gender',
  'phone_number_alt',
  'date_of_birth',
  'address',
  'bio',
]

export const GENDER_OPTIONS = [
  { value: 'male', label: 'Male' },
  { value: 'female', label: 'Female' },
  { value: 'other', label: 'Other' },
] as const

export const formatRoleLabel = (role: string | null | undefined) => {
  if (!role) return '—'
  return role
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
}

export const formatProfileDate = (value: string | null | undefined) => {
  if (!value) return '—'
  const date = dayjs(value)
  return date.isValid() ? date.format('DD MMM YYYY') : '—'
}

export const formatLastActive = (value: string | null | undefined) => {
  if (!value) return '—'
  const date = dayjs(value)
  if (!date.isValid()) return '—'
  return date.format('DD MMM YYYY · h:mm A')
}

export const mapUserToFormData = (user: User): ProfileFormData => {
  const gender = user.profile?.gender
  return {
    first_name: user.first_name ?? '',
    last_name: user.last_name ?? '',
    email: user.email ?? '',
    gender:
      gender === 'male' || gender === 'female' || gender === 'other' ? gender : undefined,
    phone_number_alt: user.profile?.phone_number_alt ?? '',
    date_of_birth: user.profile?.date_of_birth ?? '',
    address: user.profile?.address ?? '',
    bio: user.profile?.bio ?? '',
  }
}

type BuildProfileUpdateOptions = {
  dirtyFields: Partial<Record<keyof ProfileFormData, boolean>>
  profilePicture?: File | null
  includeProfilePicture?: boolean
}

export const buildProfileUpdateFormData = (
  data: ProfileFormData,
  { dirtyFields, profilePicture, includeProfilePicture = false }: BuildProfileUpdateOptions,
) => {
  const payload = new FormData()

  for (const field of PROFILE_FORM_FIELDS) {
    if (!dirtyFields[field]) continue
    const value = data[field]
    if (value === undefined) continue
    payload.append(field, value === '' ? '' : String(value))
  }

  if (includeProfilePicture && profilePicture) {
    payload.append('profile_picture', profilePicture)
  }

  return payload
}

export const hasProfileUpdateChanges = (
  dirtyFields: Partial<Record<keyof ProfileFormData, boolean>>,
  includeProfilePicture: boolean,
) => Object.values(dirtyFields).some(Boolean) || includeProfilePicture
