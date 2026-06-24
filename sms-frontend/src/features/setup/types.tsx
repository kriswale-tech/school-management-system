export interface Step {
  step: string
  name: string
  completed: boolean
}

export interface Setup {
  id: number
  steps: Step[]
  current_step: string
  progress_percentage: number
  started_at: string
  completed_at: string
  updated_at: string
  school: string
}

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

export interface SetupProgressResponse {
  next_step: string
  completed_steps: string[]
  is_complete: boolean
  progress_percentage: number
}
