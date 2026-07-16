export interface SchoolProfileFormData {
  school_name: string
  motto: string
  address: string
  gps_address: string
  po_box?: string
  phone_number: string
  phone_number_alt?: string
  email: string
}

export interface SchoolProfile {
  id: string
  created_at: string
  updated_at: string
  name: string
  address: string
  gps_address: string
  box_address: string
  phone_number: string
  phone_number_alt: string
  email: string
  logo: string
  motto: string
  setup_completed: boolean
  setup_completed_at: string
}
