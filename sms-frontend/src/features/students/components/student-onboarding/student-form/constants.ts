import type { ChoiceItem } from '@/components/shared/ChoicePillGroup'
import type { FormStepDefinition, StudentFormValues } from './types'

export const STUDENT_FORM_STEPS: FormStepDefinition[] = [
  {
    id: 'basic',
    label: 'Basic Details',
    fields: [
      'first_name',
      'last_name',
      'other_names',
      'gender',
      'date_of_birth',
      'admission_date',
    ],
  },
  {
    id: 'guardian',
    label: 'Guardian Info',
    fields: ['guardians'],
  },
  {
    id: 'placement',
    label: 'Class Placement',
    fields: ['stream_id', 'is_new_student'],
  },
]

export const GENDER_OPTIONS = [
  { value: 'male', label: 'Male' },
  { value: 'female', label: 'Female' },
  { value: 'other', label: 'Other' },
] as const

export const RELATIONSHIP_OPTIONS = [
  { value: 'father', label: 'Father' },
  { value: 'mother', label: 'Mother' },
  { value: 'guardian', label: 'Guardian' },
  { value: 'uncle', label: 'Uncle' },
  { value: 'aunt', label: 'Aunt' },
  { value: 'cousin', label: 'Cousin' },
  { value: 'sibling', label: 'Sibling' },
  { value: 'grandparent', label: 'Grandparent' },
  { value: 'other', label: 'Other' },
] as const

export const STUDENT_STATUS_OPTIONS: ChoiceItem<boolean>[] = [
  { label: 'New Student', value: true },
  { label: 'Continuing Student', value: false },
]

export const GUARDIAN_MODE_OPTIONS: ChoiceItem<'new' | 'existing'>[] = [
  { label: 'New guardian', value: 'new' },
  { label: 'Existing parent', value: 'existing' },
]

export const DEFAULT_GUARDIAN: StudentFormValues['guardians'][number] = {
  mode: 'new',
  parent_id: '',
  name: '',
  phone_number: '',
  email: '',
  relationship: '',
}

export const DEFAULT_STUDENT_FORM_VALUES: StudentFormValues = {
  first_name: '',
  last_name: '',
  other_names: '',
  gender: '',
  date_of_birth: '',
  admission_date: '',
  guardians: [{ ...DEFAULT_GUARDIAN }],
  stream_id: '',
  is_new_student: null,
}
