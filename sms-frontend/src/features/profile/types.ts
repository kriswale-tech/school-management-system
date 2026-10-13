export type ProfileGender = 'male' | 'female' | 'other'

export interface ProfileFormData {
  first_name: string
  last_name: string
  email: string
  gender?: ProfileGender
  phone_number_alt: string
  date_of_birth: string
  address: string
  bio: string
}
