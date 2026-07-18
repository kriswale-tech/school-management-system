import type { FeeItem, FeeItemFormValues, StudentType } from './types'
import type { ChoiceItem } from '@/components/shared/ChoicePillGroup'

export const ENTIRE_SCHOOL_VALUE = 'entire_school'

export const STUDENT_TYPE_OPTIONS: ChoiceItem[] = [
  { label: 'All Students', value: 'all_students' },
  { label: 'New Students Only', value: 'new_students' },
  { label: 'Continuing Students Only', value: 'continuing_students' },
]

export const buildAppliesToGroupsOptions = (
  levels: { id: string; name: string }[],
  classes: { id: string; name: string }[],
): ChoiceItem[] => [
  { label: 'Entire School', value: ENTIRE_SCHOOL_VALUE },
  {
    label: 'Level',
    options: levels.map((level) => ({
      label: level.name,
      value: `level:${level.id}`,
    })),
  },
  {
    label: 'Class',
    options: classes.map((classItem) => ({
      label: classItem.name,
      value: `class:${classItem.id}`,
    })),
  },
]

export const mapAppliesToGroupsToPayload = (
  value: string,
): Pick<FeeItemFormValues, 'applies_to_type' | 'applies_to_id'> => {
  if (value === ENTIRE_SCHOOL_VALUE) {
    return { applies_to_type: 'school', applies_to_id: null }
  }

  if (value.startsWith('level:')) {
    return { applies_to_type: 'level', applies_to_id: value.slice('level:'.length) }
  }

  if (value.startsWith('class:')) {
    return { applies_to_type: 'class', applies_to_id: value.slice('class:'.length) }
  }

  return { applies_to_type: 'school', applies_to_id: null }
}

export const mapStudentTypeToPayload = (value: string): StudentType => {
  if (value === 'new_students') return 'new_student'
  if (value === 'continuing_students') return 'continuing_student'
  return 'all_students'
}

export const mapStudentTypeFromApi = (value: StudentType): string => {
  if (value === 'new_student') return 'new_students'
  if (value === 'continuing_student') return 'continuing_students'
  return 'all_students'
}

export const mapAppliesToGroupsFromApi = (item: FeeItem): string => {
  if (item.applies_to_type === 'school') return ENTIRE_SCHOOL_VALUE
  return `${item.applies_to_type}:${item.applies_to_id}`
}

export const buildAppliesToDisplay = (item: FeeItem) =>
  `${item.student_type_display} in ${item.applies_to_name}`

export const formatFeeAmount = (amount: string) => {
  const parsed = Number(amount)
  if (Number.isNaN(parsed)) return amount

  return new Intl.NumberFormat('en-GH', {
    style: 'currency',
    currency: 'GHS',
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(parsed)
}

export const buildFeeItemPayload = (values: {
  name: string
  amount: string
  appliesToGroups: string
  appliesToStudents: string
}): FeeItemFormValues => {
  const appliesTo = mapAppliesToGroupsToPayload(values.appliesToGroups)

  return {
    name: values.name.trim(),
    amount: values.amount.trim(),
    description: '',
    applies_to_type: appliesTo.applies_to_type,
    applies_to_id: appliesTo.applies_to_id,
    student_type: mapStudentTypeToPayload(values.appliesToStudents),
  }
}

export const validateFeeItemForm = (values: {
  name: string
  amount: string
  appliesToGroups: string
  appliesToStudents: string
}): string | null => {
  if (!values.name.trim()) return 'Fee name is required'

  const amount = Number(values.amount)
  if (!values.amount.trim() || Number.isNaN(amount) || amount <= 0) {
    return 'Amount must be a valid number greater than 0'
  }

  if (!values.appliesToGroups) return 'Please select who this fee applies to (Groups)'
  if (!values.appliesToStudents) return 'Please select who this fee applies to (Students)'

  return null
}
