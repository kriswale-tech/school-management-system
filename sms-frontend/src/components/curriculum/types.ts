export type SubjectScope = 'class' | 'level'

export interface StreamForSetup {
  id: string
  name: string
  full_name: string
  description: string | null
  is_default: boolean
  is_active: boolean
  capacity: number | null
}

export interface SubjectGroupForSetup {
  id?: string
  name: string
  is_active?: boolean
}

export interface SubjectForSetup {
  id?: string
  name: string
  is_active?: boolean
  is_system_generated?: boolean
  is_editable: boolean
  class_ids: string[]
  groups: SubjectGroupForSetup[]
}

export interface ClassSubjectForSetup extends Omit<SubjectForSetup, 'class_ids'> {
  id: string
  class_subject_id: string
}

export interface ClassForSetup {
  id?: string
  name: string
  description?: string | null
  order?: number
  is_active?: boolean
  is_system_generated?: boolean
  is_editable: boolean
  streams?: StreamForSetup[]
  subjects?: ClassSubjectForSetup[]
}

export interface LevelForSetup {
  id?: string
  name: string
  description?: string | null
  order?: number
  is_active?: boolean
  is_system_generated?: boolean
  subject_scope: SubjectScope
  allows_custom_classes: boolean
  classes: ClassForSetup[]
  subjects: SubjectForSetup[]
}

export type LevelWithRelatedClassesAndSubjects = LevelForSetup[]
