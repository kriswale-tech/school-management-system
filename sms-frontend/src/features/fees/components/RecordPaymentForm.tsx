import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import {
  Button,
  FormLabel,
  InputField,
  SearchAndSelect,
  SelectField,
} from '@/components/ui'
import { getStudents } from '@/features/students/services'
import type { Student } from '@/features/students/types'
import {
  STUDENT_FEE_HISTORY_QUERY_KEY,
  STUDENT_FEES_QUERY_KEY,
  STUDENT_PAYMENTS_QUERY_KEY,
} from '@/features/students/utils'
import dayjs from '@/lib/dayjs'
import { getApiErrorMessage } from '@/utils'
import { getReceiptDetail, getStudentPaymentTarget, recordPayment } from '../services'
import type { RecordPaymentResponse } from '../types'
import {
  FEE_DESK_QUERY_KEY,
  FEE_DESK_STATS_QUERY_KEY,
  PAYMENT_METHOD_OPTIONS,
  STUDENT_PAYMENT_TARGET_QUERY_KEY,
  formatFeeAmount,
} from '../utils'
import { openReceiptPrintWindow } from '../utils/receiptPrint'
import StudentPaymentSummary from './StudentPaymentSummary'

const STUDENT_SEARCH_DEBOUNCE_MS = 300
const STUDENT_PAGE_SIZE = 20

type RecordPaymentFormProps = {
  preselectedStudentId?: string
  onCancel?: () => void
}

const getStudentFullName = (student: Student) =>
  [student.first_name, student.other_names, student.last_name].filter(Boolean).join(' ')

const getStudentClassLabel = (student: Student) =>
  student.stream?.full_name ?? student.class_level?.name ?? '—'

const RecordPaymentForm = ({
  preselectedStudentId,
  onCancel,
}: RecordPaymentFormProps) => {
  const queryClient = useQueryClient()
  const [studentId, setStudentId] = useState(preselectedStudentId ?? '')
  const [searchValue, setSearchValue] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [amountEdited, setAmountEdited] = useState(false)
  const [amountDraft, setAmountDraft] = useState('')
  const [paymentMethod, setPaymentMethod] = useState('')
  const [paidAt, setPaidAt] = useState(dayjs().format('YYYY-MM-DD'))
  const [successResult, setSuccessResult] = useState<RecordPaymentResponse | null>(null)
  const [isPrinting, setIsPrinting] = useState(false)

  const isPreselected = Boolean(preselectedStudentId)

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setDebouncedSearch(searchValue.trim())
    }, STUDENT_SEARCH_DEBOUNCE_MS)
    return () => window.clearTimeout(timer)
  }, [searchValue])

  const { data: studentsData, isLoading: studentsLoading } = useQuery({
    queryKey: ['students', 'record-payment-search', debouncedSearch],
    queryFn: () =>
      getStudents({
        search: debouncedSearch || undefined,
        page_size: STUDENT_PAGE_SIZE,
      }),
    enabled: !isPreselected,
  })

  const students = useMemo(() => studentsData?.results ?? [], [studentsData?.results])

  const studentOptions = useMemo(
    () =>
      students.map((student) => ({
        value: student.id,
        label: `${getStudentFullName(student)} - ${getStudentClassLabel(student)} - ${student.student_id}`,
      })),
    [students],
  )

  const {
    data: paymentTarget,
    isLoading: targetLoading,
    isFetching: targetFetching,
  } = useQuery({
    queryKey: [STUDENT_PAYMENT_TARGET_QUERY_KEY, studentId],
    queryFn: () => getStudentPaymentTarget(studentId),
    enabled: Boolean(studentId),
  })

  const suggestedAmount = paymentTarget?.has_outstanding
    ? paymentTarget.all_time_outstanding
    : ''
  const amount = amountEdited ? amountDraft : suggestedAmount

  const handleStudentChange = (nextStudentId: string) => {
    setStudentId(nextStudentId)
    setAmountEdited(false)
    setAmountDraft('')
  }

  const resetForAnotherPayment = () => {
    setSuccessResult(null)
    setAmountEdited(false)
    setAmountDraft('')
    setPaymentMethod('')
    setPaidAt(dayjs().format('YYYY-MM-DD'))
    if (!isPreselected) {
      setStudentId('')
      setSearchValue('')
      setDebouncedSearch('')
    }
  }

  const { mutate: submitPayment, isPending } = useMutation({
    mutationFn: recordPayment,
    onSuccess: async (response) => {
      const advanceNote =
        Number(response.advance_created) > 0
          ? ` · Advance ${formatFeeAmount(response.advance_created)} held`
          : ''
      toast.success(`Payment recorded · Receipt ${response.receipt_number}${advanceNote}`)
      setSuccessResult(response)
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: [FEE_DESK_QUERY_KEY] }),
        queryClient.invalidateQueries({ queryKey: [FEE_DESK_STATS_QUERY_KEY] }),
        queryClient.invalidateQueries({ queryKey: [STUDENT_FEES_QUERY_KEY] }),
        queryClient.invalidateQueries({ queryKey: [STUDENT_FEE_HISTORY_QUERY_KEY] }),
        queryClient.invalidateQueries({ queryKey: [STUDENT_PAYMENTS_QUERY_KEY] }),
        queryClient.invalidateQueries({ queryKey: [STUDENT_PAYMENT_TARGET_QUERY_KEY] }),
      ])
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, 'Unable to record payment.'))
    },
  })

  const canSubmit =
    Boolean(studentId) &&
    Boolean(paymentTarget?.has_outstanding) &&
    Boolean(amount) &&
    Number(amount) > 0 &&
    Boolean(paymentMethod) &&
    Boolean(paidAt)

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    if (!canSubmit || !studentId) return

    submitPayment({
      student_id: studentId,
      amount,
      payment_method: paymentMethod as (typeof PAYMENT_METHOD_OPTIONS)[number]['value'],
      paid_at: dayjs(`${paidAt}T12:00:00`).toISOString(),
    })
  }

  const handlePrintReceipt = async () => {
    if (!successResult || isPrinting) return
    setIsPrinting(true)
    try {
      const receipt = await getReceiptDetail(successResult.receipt_id)
      openReceiptPrintWindow(receipt)
    } catch (error) {
      toast.error(
        error instanceof Error && error.message.includes('Pop-up')
          ? error.message
          : getApiErrorMessage(error, 'Unable to open receipt for printing.'),
      )
    } finally {
      setIsPrinting(false)
    }
  }

  if (successResult) {
    const advanceCreated = Number(successResult.advance_created) > 0
    return (
      <div className="space-y-5">
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 px-4 py-4 space-y-2">
          <p className="text-sm font-medium text-emerald-900">Payment recorded</p>
          <p className="text-sm text-emerald-800">
            Receipt {successResult.receipt_number} ·{' '}
            {formatFeeAmount(successResult.amount)}
          </p>
          {successResult.allocations.length > 1 ? (
            <ul className="text-sm text-emerald-800 space-y-1 pt-1">
              {successResult.allocations.map((row) => (
                <li key={row.term_id}>
                  {row.term_label}: {formatFeeAmount(row.amount)}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-emerald-800">{successResult.term_label}</p>
          )}
          {advanceCreated ? (
            <p className="text-sm text-emerald-800">
              Advance held: {formatFeeAmount(successResult.advance_created)}
            </p>
          ) : null}
          <p className="text-sm text-emerald-800">
            Outstanding after: {formatFeeAmount(successResult.outstanding_after)}
          </p>
        </div>

        <div className="flex flex-col gap-2 border-t border-slate-200 pt-4">
          <Button
            type="button"
            className="w-full"
            loading={isPrinting}
            onClick={handlePrintReceipt}
          >
            Print receipt
          </Button>
          <Button type="button" variant="outline" className="w-full" onClick={resetForAnotherPayment}>
            Record another
          </Button>
          <Button type="button" variant="ghost" className="w-full" onClick={onCancel}>
            Cancel
          </Button>
        </div>
      </div>
    )
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div className="space-y-5">
        <StudentPaymentSummary
          target={paymentTarget ?? null}
          isLoading={Boolean(studentId) && (targetLoading || targetFetching)}
        />

        {!isPreselected ? (
          <div className="space-y-2">
            <FormLabel label="Select Student" required />
            <SearchAndSelect
              value={studentId}
              onChange={handleStudentChange}
              searchValue={searchValue}
              onSearchChange={setSearchValue}
              options={studentOptions}
              placeholder="Search student by name or ID"
              searchPlaceholder="Search by name or student ID"
              loading={studentsLoading}
              emptyMessage={
                debouncedSearch ? 'No students found' : 'Type to search students'
              }
            />
          </div>
        ) : null}

        <div className="space-y-2">
          <FormLabel label="Target Term" required />
          <InputField
            value={paymentTarget?.target_term?.label ?? ''}
            placeholder="Assigned when a student is selected"
            disabled
            readOnly
            className="bg-white"
          />
          <p className="text-sm text-slate-500">
            Starts at the earliest owing term. Larger amounts cascade to later terms.
          </p>
        </div>

        <div className="space-y-2">
          <FormLabel label="Amount to Pay" required />
          <div className="flex items-stretch overflow-hidden rounded-lg border border-slate-300">
            <span className="flex items-center bg-slate-200 px-3 text-sm text-slate-600 shrink-0">
              GHS
            </span>
            <InputField
              type="number"
              min="0"
              step="0.01"
              value={amount}
              onChange={(event) => {
                setAmountEdited(true)
                setAmountDraft(event.target.value)
              }}
              disabled={!paymentTarget?.has_outstanding}
              wrapperClassName="min-w-0 flex-1"
              className="rounded-none border-none bg-white py-3"
            />
          </div>
          <p className="text-sm text-slate-500">
            Pre-filled with all-time owing. Only surplus after clearing every owing term becomes
            advance.
            {paymentTarget?.has_outstanding
              ? ` All-time owing: ${formatFeeAmount(paymentTarget.all_time_outstanding)}.`
              : ''}
          </p>
        </div>

        <div className="space-y-2">
          <FormLabel label="Method of Payment" required />
          <SelectField
            options={[...PAYMENT_METHOD_OPTIONS]}
            value={paymentMethod}
            onChange={setPaymentMethod}
            placeholder="Select payment method"
            disabled={!paymentTarget?.has_outstanding}
          />
        </div>

        <div className="space-y-2">
          <FormLabel label="Payment Date" required />
          <InputField
            type="date"
            value={paidAt}
            onChange={(event) => setPaidAt(event.target.value)}
            disabled={!paymentTarget?.has_outstanding}
            className="bg-white"
          />
        </div>
      </div>

      <div className="flex gap-2 border-t border-slate-200 pt-4">
        <Button type="button" variant="outline" className="flex-1" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" className="flex-1" loading={isPending} disabled={!canSubmit}>
          Record Fees
        </Button>
      </div>
    </form>
  )
}

export default RecordPaymentForm
