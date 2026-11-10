export type SchoolStatus = 'pending' | 'active' | 'suspended' | 'archived'

export type SchoolCategory =
  | 'creche'
  | 'nursery'
  | 'kindergarten'
  | 'primary'
  | 'jhs'
  | 'shs'
  | 'mixed'
  | 'other'
  | ''

export type PlatformSchoolListAdmin = {
  full_name: string
  phone_number: string
  email: string
}

export type PlatformSchoolSummary = {
  school_count: number
  active_school_count: number
  student_count: number
  staff_count: number
  overdue_school_count: number
}

export type PlatformSchoolListItem = {
  id: string
  name: string
  phone_number: string
  email: string | null
  region: string
  category: string
  status: SchoolStatus
  setup_completed: boolean
  /** Active SchoolMembership rows (admins, teachers, staff, accountants). */
  staff_count: number
  student_count: number
  plan_name: string | null
  plan_code: string | null
  subscription_status: string | null
  subscription_interval: string | null
  next_renewal_at: string | null
  payment_overdue: boolean
  admins: PlatformSchoolListAdmin[]
  activated_at: string | null
  suspended_at: string | null
  created_at: string
}

export type SchoolAdminInvite = {
  id: string
  school: string
  school_name: string
  phone_number: string
  email: string
  first_name: string
  last_name: string
  status: string
  expires_at: string
  accepted_at: string | null
  created_at: string
  accept_url: string
}

export type PlatformSchoolDetail = {
  id: string
  name: string
  address: string | null
  phone_number: string
  phone_number_alt: string | null
  email: string | null
  region: string
  category: string
  status: SchoolStatus
  setup_completed: boolean
  activated_at: string | null
  suspended_at: string | null
  created_at: string
  updated_at: string
  staff_count?: number
  student_count?: number
  admins: Array<{
    membership_id: string
    user_id: string
    phone_number: string
    email: string
    full_name: string
    is_active: boolean
  }>
  invites: SchoolAdminInvite[]
}

export type Paginated<T> = {
  count: number
  results: T[]
  next: string | null
  previous: string | null
}
