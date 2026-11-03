import type { AllClassesLevel, ClassEntry } from '@/features/classes/types'
import type {
  GuardianNotifyChannel,
  GuardianRelationship,
  StudentGender,
  StudentOnboardPayload,
} from '@/features/students/types'

export type StudentFormStepId = 'basic' | 'guardian' | 'placement'

export type GuardianMode = 'new' | 'existing'

export type GuardianFormValues = {
  mode: GuardianMode
  parent_id: string
  name: string
  phone_number: string
  email: string
  notify_channel: GuardianNotifyChannel
  relationship: GuardianRelationship | ''
}

export type StudentFormValues = {
  student_id: string
  first_name: string
  last_name: string
  other_names: string
  gender: StudentGender | ''
  date_of_birth: string
  admission_date: string
  guardians: GuardianFormValues[]
  stream_id: string
  is_new_student: boolean | null
}

export type ClassOption = ClassEntry

export type LevelOption = AllClassesLevel

export type FormStepDefinition = {
  id: StudentFormStepId
  label: string
  fields: (keyof StudentFormValues)[]
}

export type StudentFormSubmitValues = StudentOnboardPayload
