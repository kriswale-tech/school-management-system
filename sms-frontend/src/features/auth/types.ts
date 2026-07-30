
export interface SignupData {
  school_name: string
  first_name: string
  last_name: string
  phone_number: string
  email: string
}

export interface VerifyOTPData {
  phone_number: string
  otp: string
}

export interface SelectSchoolData {
  school_id: string
}

export interface Profile {
  profile_picture: string
  bio: string
  date_of_birth: string
  gender: string
  address: string
  phone_number_alt: string
}

/** One school the user can act in; used by the school picker. */
export interface SchoolMembership {
  id: string
  school_id: string
  school_name: string
  school_logo: string | null
  role: string
  school_setup_completed: boolean
  last_active_at: string | null
}

export interface User {
  id: string
  full_name: string
  first_name: string
  last_name: string
  phone_number: string
  email: string
  /** Null while the session is identity-only (school not selected). */
  role: string | null
  is_active: boolean
  profile: Profile
  /** Null while the session is identity-only (school not selected). */
  school_setup_completed: boolean | null
  /** Null while the session is identity-only (school not selected). */
  school_id: string | null
  schools: SchoolMembership[]
  requires_school_selection: boolean
}

/** Login / OTP / select-school response body (cookies carry the tokens). */
export interface AuthResponse {
  message: string
  requires_school_selection: boolean
  active_school: SchoolMembership | null
  schools: SchoolMembership[]
}
