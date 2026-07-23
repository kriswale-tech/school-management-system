import type { StaffFormData } from './types'

type BuildStaffFormDataOptions = {
  role: string
  profilePicture?: File | null
}

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
