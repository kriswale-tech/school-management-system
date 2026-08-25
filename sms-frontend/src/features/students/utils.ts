import dayjs from '@/lib/dayjs'
import type { FeePaymentStatus, StudentGender } from './types'

/** Builds a sparse PATCH body from react-hook-form dirtyFields. */
export function pickDirtyFields<T extends Record<string, unknown>>(
  data: T,
  dirtyFields: Partial<Record<keyof T, boolean | object>>,
): Partial<T> {
  const payload: Partial<T> = {}

  for (const key of Object.keys(dirtyFields) as (keyof T)[]) {
    if (!dirtyFields[key]) continue
    payload[key] = data[key]
  }

  return payload
}

export const hasDirtyChanges = (
  dirtyFields: Partial<Record<string, boolean | object>>,
): boolean => Object.values(dirtyFields).some(Boolean)

export const formatStudentDate = (value: string) => {
  const date = dayjs(value)
  return date.isValid() ? date.format('DD MMM YYYY') : '—'
}

export const formatGenderLabel = (gender: StudentGender | string) => {
  if (!gender) return '—'
  return gender.charAt(0).toUpperCase() + gender.slice(1)
}

export const formatFeeAmount = (amount: string | number) => {
  const parsed = typeof amount === 'number' ? amount : Number(amount)
  if (Number.isNaN(parsed)) return String(amount)

  return new Intl.NumberFormat('en-GH', {
    style: 'currency',
    currency: 'GHS',
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(parsed)
}

export const getFeePaymentStatusClass = (status: FeePaymentStatus | string) => {
  if (status === 'fully_paid') return 'text-green-600'
  if (status === 'no_fees') return 'text-slate-500'
  return 'text-red-600'
}

export const STUDENT_DETAIL_QUERY_KEY = 'student-detail' as const
export const STUDENT_FEES_QUERY_KEY = 'student-fees' as const
export const STUDENT_FEE_HISTORY_QUERY_KEY = 'student-fee-history' as const
export const STUDENT_PAYMENTS_QUERY_KEY = 'student-payments' as const
