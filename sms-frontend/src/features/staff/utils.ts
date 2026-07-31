import type { StaffFormData, StaffGender, StaffProfile } from './types'

type BuildStaffFormDataOptions = {
  role: string
  profilePicture?: File | null
}

export const DEFAULT_PROFILE_IMAGE = '/images/default_profile.webp'

const STAFF_FORM_FIELDS: (keyof StaffFormData)[] = [
  'first_name',
  'last_name',
  'phone_number',
  'gender',
  'phone_number_alt',
  'email',
  'date_of_birth',
  'address',
]

/** Builds multipart FormData ready for POST to `/accounts/users/`. */
export function buildStaffFormData(data: StaffFormData, options: BuildStaffFormDataOptions) {
  const payload = new FormData()

  payload.append('role', options.role)
  payload.append('first_name', data.first_name)
  payload.append('last_name', data.last_name)
  payload.append('phone_number', data.phone_number)

  if (data.gender) payload.append('gender', data.gender)
  if (data.phone_number_alt) payload.append('phone_number_alt', data.phone_number_alt)
  if (data.email) payload.append('email', data.email)
  if (data.date_of_birth) payload.append('date_of_birth', data.date_of_birth)
  if (data.address) payload.append('address', data.address)

  if (options.profilePicture) {
    payload.append('profile_picture', options.profilePicture)
  }

  return payload
}

type BuildStaffUpdateFormDataOptions = {
  dirtyFields: Partial<Record<keyof StaffFormData, boolean>>
  profilePicture?: File | null
  includeProfilePicture?: boolean
}

/** Builds multipart FormData with only changed fields for PATCH to `/accounts/users/:id/`. */
export function buildStaffUpdateFormData(
  data: StaffFormData,
  { dirtyFields, profilePicture, includeProfilePicture = false }: BuildStaffUpdateFormDataOptions,
) {
  const payload = new FormData()

  for (const field of STAFF_FORM_FIELDS) {
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

export const hasStaffUpdateChanges = (
  dirtyFields: Partial<Record<keyof StaffFormData, boolean>>,
  includeProfilePicture: boolean,
) => Object.values(dirtyFields).some(Boolean) || includeProfilePicture

export const getStaffProfileImage = (staff: { profile: Pick<StaffProfile, 'profile_picture'> }) =>
  staff.profile.profile_picture ?? DEFAULT_PROFILE_IMAGE

export const mapStaffToFormData = (staff: {
  first_name: string
  last_name: string
  phone_number: string
  email: string | null
  profile: Pick<StaffProfile, 'gender' | 'phone_number_alt' | 'date_of_birth' | 'address'>
}): StaffFormData => {
  const gender = staff.profile.gender

  return {
    first_name: staff.first_name,
    last_name: staff.last_name,
    gender: gender === 'male' || gender === 'female' ? (gender as StaffGender) : undefined,
    phone_number: staff.phone_number,
    phone_number_alt: staff.profile.phone_number_alt ?? '',
    email: staff.email ?? '',
    date_of_birth: staff.profile.date_of_birth ?? '',
    address: staff.profile.address ?? '',
  }
}

export const formatStaffRole = (role: string) =>
  role
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ')
