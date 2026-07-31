export type StudentQueryParams = {
  page?: number
  page_size?: number
  search?: string
  sort?: string
  order?: string
  class_level?: string
  stream?: string
  term?: string
}

export interface StudentClassLevel {
  id: string
  name: string
}

export interface StudentStream {
  id: string
  name: string
  full_name: string
  is_default: boolean
}

export interface PrimaryParent {
  id: string
  name: string
  relationship: string
  phone_number: string
  email: string
  phone_number_alt: string
}


export interface Student {
  id: string
  student_id: string
  first_name: string
  last_name: string
  other_names: string
  gender: string
  date_of_birth: string
  admission_date: string
  class_level: StudentClassLevel
  stream: StudentStream
  is_new_student: boolean
  payment_status: string
  primary_parent: PrimaryParent
}

export interface StudentStats {
  term_id: string
  total_students: number
  new_students: number
  continuing_students: number
  boys: number
  girls: number
  fully_paid: number
  partially_paid: number
  owing: number
  no_fees: number
}

export type StudentGender = 'male' | 'female' | 'other'

export type GuardianRelationship =
  | 'father'
  | 'mother'
  | 'guardian'
  | 'other'
  | 'uncle'
  | 'aunt'
  | 'cousin'
  | 'sibling'
  | 'grandparent'

export type Parent = {
  id: string
  name: string
  phone_number: string
  email: string
}

export type ParentQueryParams = {
  page?: number
  page_size?: number
  search?: string
}

export type GuardianInput =
  | {
      parent_id: string
      relationship: GuardianRelationship
    }
  | {
      name: string
      phone_number: string
      email: string
      relationship: GuardianRelationship
    }

export type StudentOnboardPayload = {
  first_name: string
  last_name: string
  other_names: string
  gender: StudentGender
  date_of_birth: string
  admission_date: string
  guardians: GuardianInput[]
  stream_id: string
  is_new_student: boolean
}