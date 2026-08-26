export type StaffGender = 'male' | 'female'

export type StaffQueryParams = {
  page?: number
  page_size?: number
  search?: string
  role?: string
  is_active?: boolean
  exclude?: string
}

/** Query params for the staff directory list and filter-aware stats. */
export type StaffDeskQueryParams = {
  page?: number
  page_size?: number
  search?: string
  role?: string
  is_active?: boolean
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

/** Roles available when adding staff from the directory. */
export const STAFF_DESK_ROLE_OPTIONS = [
  { value: 'admin', label: 'Admin' },
  { value: 'teacher', label: 'Teacher' },
  { value: 'accountant', label: 'Accountant' },
  { value: 'staff', label: 'Staff' },
] as const

/** Role filter options for the directory ActionBar. */
export const STAFF_DESK_FILTER_OPTIONS = [
  { value: 'admin', label: 'Admin' },
  { value: 'teacher', label: 'Teacher' },
  { value: 'accountant', label: 'Accountant' },
  { value: 'staff', label: 'Staff' },
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

/** Row from GET /accounts/staff/ */
export interface StaffDeskRow {
  id: string
  membership_id: string
  full_name: string
  first_name: string
  last_name: string
  email: string | null
  phone_number: string
  role: string
  is_active: boolean
  date_added: string
  profile_picture: string | null
  is_class_teacher: boolean
  is_subject_teacher: boolean
}

/** Response from GET /accounts/staff/stats/ */
export interface StaffDeskStats {
  total_staff: number
  teachers: number
  accountants: number
  admins: number
}

export interface StaffDeskClassTeacherAssignment {
  id: string
  class_level_id: string
  class_level_name: string
  stream_id: string | null
  stream_name: string | null
  display_name: string
  students_count: number
}

export interface StaffDeskTeachingAssignment {
  id: string
  class_subject_id: string
  class_level_id: string
  class_level_name: string
  subject_id: string
  subject_name: string
  stream_id: string | null
  stream_name: string | null
  subject_group_id: string | null
  subject_group_name: string | null
  display_class_name: string
  students_count: number
}

/** Response from GET /accounts/staff/:id/ */
export interface StaffDeskDetail extends StaffDeskRow {
  profile: StaffProfile | null
  school_id: string
  school_setup_completed: boolean
  class_teacher_assignments: StaffDeskClassTeacherAssignment[]
  teaching_assignments: StaffDeskTeachingAssignment[]
}

/** Minimal shape needed to edit a staff/teacher user in shared modals/forms. */
export type EditableStaffUser = {
  id: string
  role: string
  first_name: string
  last_name: string
  phone_number: string
  email: string | null
  profile: StaffProfile
}

/** PATCH /accounts/users/{id}/ — id may differ from the URL when linking an existing person. */
export interface UpdateStaffResponse {
  user: Staff
  linked_existing_user: boolean
}
