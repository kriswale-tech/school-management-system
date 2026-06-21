

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


export interface Profile {
  profile_picture: string
  bio: string
  date_of_birth: string
  gender: string
  address: string
  phone_number_alt: string
}

export interface User {
  id: string
  full_name: string
  first_name: string
  last_name: string
  phone_number: string
  email: string
  role: string
  is_active: boolean
  profile: Profile
}