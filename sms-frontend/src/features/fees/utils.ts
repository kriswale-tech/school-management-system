import dayjs from '@/lib/dayjs'
import { formatFeeAmount } from '@/features/students/utils'

export { formatFeeAmount }

export const FEE_DESK_QUERY_KEY = 'fee-desk' as const
export const FEE_DESK_STATS_QUERY_KEY = 'fee-desk-stats' as const
export const FEE_DESK_FILTERS_QUERY_KEY = 'fee-desk-filters' as const
export const FEE_STRUCTURE_QUERY_KEY = 'fee-structure' as const
export const STUDENT_PAYMENT_TARGET_QUERY_KEY = 'student-payment-target' as const

export const PAYMENT_METHOD_OPTIONS = [
  { value: 'cash', label: 'Cash' },
  { value: 'cheque', label: 'Cheque' },
  { value: 'bank_transfer', label: 'Bank Transfer' },
  { value: 'mobile_money', label: 'Mobile Money' },
  { value: 'other', label: 'Other' },
] as const

export const getFeeDeskFullName = (row: {
  first_name: string
  other_names: string
  last_name: string
}) => [row.first_name, row.other_names, row.last_name].filter(Boolean).join(' ')

export const formatFeeTransactionDate = (value: string | null) => {
  if (!value) return '—'
  const date = dayjs(value)
  return date.isValid() ? date.format('DD MMM YYYY') : '—'
}

export const formatDebtorsStat = (debtors: number, totalStudents: number) =>
  `${debtors}/${totalStudents}`
