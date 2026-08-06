export type ClassEntry = {
  id: string
  class_level_id: string
  display_name: string
  student_count: number
  is_default: boolean
}

export type AllClassesLevel = {
  id: string
  name: string
  order: number
  classes: ClassEntry[]
}

export type AllClassesResponse = {
  term_id: string
  levels: AllClassesLevel[]
}

export type AllClassesQueryParams = {
  term?: string
}

export type ClassTeacherSummary = {
  id: string
  full_name: string
}

export type ClassListItem = {
  id: string
  name: string
  level_id: string
  level_name: string
  class_level_id: string
  class_level_name: string
  students_count: number
  subjects_count: number
  unassigned_subjects_count: number
  class_teacher: ClassTeacherSummary | null
  is_default: boolean
  is_assigned: boolean
  needs_attention: boolean
  capacity: number | null
}

export type ClassListResponse = {
  term_id: string
  results: ClassListItem[]
}

export type ClassListQueryParams = {
  term?: string
  search?: string
}

export type ClassStats = {
  term_id: string
  total_classes: number
  total_students: number
  total_teachers_assigned: number
  unassigned_classes: number
  unassigned_class_subjects: number
  empty_classes: number
  classes_with_students: number
}

export type ClassDetail = {
  id: string
  name: string
  level_id: string
  level_name: string
  class_level_id: string
  class_level_name: string
  students_count: number
  subjects_count: number
  unassigned_subjects_count: number
  class_teacher: ClassTeacherSummary | null
  class_teacher_assignment_id: string | null
  is_default: boolean
  is_assigned: boolean
  needs_attention: boolean
  capacity: number | null
  term_id: string
}

export type ClassStudent = {
  id: string
  full_name: string
  student_id: string
  admission_date: string
}

export type ClassStudentListResponse = {
  term_id: string
  results: ClassStudent[]
}

export type ClassSubjectKind = 'class_subject' | 'subject_group'

export type ClassSubjectRow = {
  id: string
  kind: ClassSubjectKind
  class_subject_id: string
  subject_group_id: string | null
  name: string
  subject_name: string
  group_name: string | null
  students_count: number
  teacher: ClassTeacherSummary | null
  teaching_assignment_id: string | null
}

export type ClassSubjectListResponse = {
  term_id: string
  results: ClassSubjectRow[]
}

export type ClassTeacherOption = {
  id: string
  full_name: string
  class_teacher_summary: string
  teaching_summary: string
}

export type ClassTeacherOptionListResponse = {
  term_id: string
  results: ClassTeacherOption[]
}

export type AssignClassTeacherPayload = {
  teacher_id: string
}

export type AssignSubjectTeacherPayload = {
  teacher_id: string
  class_subject_id: string
  subject_group_id?: string | null
}
