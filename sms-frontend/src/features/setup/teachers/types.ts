export type TeacherGender = 'male' | 'female'

export type TeacherFormData = {
  first_name: string
  last_name: string
  gender?: TeacherGender
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

export interface TeacherProfile {
  profile_picture: string | null
  bio: string | null
  date_of_birth: string | null
  gender: string | null
  address: string | null
  phone_number_alt: string | null
}

export interface ClassTeacherAssignment {
  id: string
  class_level_id: string
  class_level_name: string
  stream_id: string | null
  stream_name: string | null
}

export interface TeachingAssignment {
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
}

export interface Teacher {
  id: string
  full_name: string
  first_name: string
  last_name: string
  phone_number: string
  email: string | null
  role: string
  is_active: boolean
  profile: TeacherProfile
  class_teacher_assignments: ClassTeacherAssignment[]
  teaching_assignments: TeachingAssignment[]
}

export type TeachersResponse = Teacher[]

export type CreateClassTeacherAssignmentPayload = {
  teacher_id: string
  class_level_id: string
  stream_id: string | null
}

export type CreateTeachingAssignmentPayload = {
  teacher_id: string
  class_subject_id: string
  stream_id: string | null
  subject_group_id: string | null
}
