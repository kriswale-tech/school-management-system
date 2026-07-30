export type StaffGender = 'male' | 'female'

export type StaffQueryParams = {
  page?: number
  page_size?: number
  search?: string
  role?: string
  is_active?: boolean
  exclude?: string
}

export type StaffFormData = {
  first_name: string
  last_name: string
  gender?: StaffGender
  phone_number: string
  phone_number_alt?: string
  email?: string
  date_of_birth?: string
  address?: string
}

export const GENDER_OPTIONS = [
  { value: 'male', label: 'Male' },
  { value: 'female', label: 'Female' },
] as const

export interface StaffProfile {
    profile_picture: string | null
    bio: string | null
    date_of_birth: string | null
    gender: string | null
    address: string | null
    phone_number_alt: string | null
  }

export interface Staff {
    id: string
    full_name: string
    first_name: string
    last_name: string
    phone_number: string
    email: string | null
    role: string
    is_active: boolean
    profile: StaffProfile
    school_setup_completed: boolean
    school_id: string
    membership_id?: string
}

/** PATCH /accounts/users/{id}/ — id may differ from the URL when linking an existing person. */
export interface UpdateStaffResponse {
  user: Staff
  linked_existing_user: boolean
}