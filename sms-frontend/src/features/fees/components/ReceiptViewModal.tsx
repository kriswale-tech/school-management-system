import { useQuery } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { Button, Modal } from '@/components/ui'
import dayjs from '@/lib/dayjs'
import { getApiErrorMessage } from '@/utils'
import { getReceiptDetail } from '../services'
import { formatFeeAmount } from '../utils'
import { openReceiptPrintWindow } from '../utils/receiptPrint'

type ReceiptViewModalProps = {
  open: boolean
  receiptId: string | null
  onClose: () => void
}

const formatReceiptDateTime = (value: string) => {
  const date = dayjs(value)
  return date.isValid() ? date.format('DD MMM YYYY, HH:mm') : value
}

const ReceiptViewModal = ({ open, receiptId, onClose }: ReceiptViewModalProps) => {
  const {
    data: receipt,
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: ['fee-receipt', receiptId],
    queryFn: () => getReceiptDetail(receiptId!),
    enabled: open && Boolean(receiptId),
  })

  const handlePrint = () => {
    if (!receipt) return
    try {
      openReceiptPrintWindow(receipt)
    } catch (err) {
      toast.error(err instanceof Error ? err.message : 'Unable to open print preview')
    }
  }

  return (
    <Modal
      open={open}
      title={receipt ? `Receipt ${receipt.receipt_number}` : 'Receipt'}
      onClose={onClose}
      scrollable
      className="max-w-xl"
    >
      {isLoading ? (
        <p className="text-sm text-slate-500 py-8">Loading receipt…</p>
      ) : isError || !receipt ? (
        <p className="text-sm text-red-600 py-8" role="alert">
          {getApiErrorMessage(error, 'Unable to load receipt.')}
        </p>
      ) : (
        <div className="space-y-4">
          <div className="overflow-hidden rounded-2xl border border-slate-200 bg-white">
            <div className="h-1 bg-sky-700" aria-hidden />
            <div className="px-8 py-7">
              <div className="flex items-start gap-4">
                {receipt.school_logo_url ? (
                  <img
                    src={receipt.school_logo_url}
                    alt={`${receipt.school_name} logo`}
                    className="h-14 w-auto max-w-[140px] shrink-0 object-contain"
                  />
                ) : null}
                <div className="min-w-0">
                  <h3 className="text-[22px] font-semibold tracking-tight text-slate-900">
                    {receipt.school_name}
                  </h3>
                  <p className="mt-1 text-sm leading-relaxed text-slate-500">
                    {receipt.school_address ? (
                      <>
                        {receipt.school_address}
                        <br />
                      </>
                    ) : null}
                    {[receipt.school_phone, receipt.school_email].filter(Boolean).join(' · ')}
                  </p>
                </div>
              </div>

              <p className="mt-6 text-[32px] font-bold tracking-tight text-slate-900">
                {formatFeeAmount(receipt.amount)}
              </p>
              <p className="mt-2 mb-6 text-sm text-slate-500">Payment received</p>

              <dl className="grid grid-cols-[140px_1fr] gap-x-4 gap-y-2.5 text-sm">
                <dt className="text-slate-500">Receipt</dt>
                <dd className="font-medium text-slate-900">{receipt.receipt_number}</dd>
                <dt className="text-slate-500">Student</dt>
                <dd className="font-medium text-slate-900">
                  {receipt.student_name} ({receipt.student_id})
                </dd>
                <dt className="text-slate-500">Term</dt>
                <dd className="font-medium text-slate-900">{receipt.term_label}</dd>
                {receipt.allocations.length > 1 ? (
                  <>
                    <dt className="text-slate-500">Applied to</dt>
                    <dd className="font-medium text-slate-900">
                      {receipt.allocations.map((row) => (
                        <p key={row.term_label}>
                          {row.term_label}: {formatFeeAmount(row.amount)}
                        </p>
                      ))}
                    </dd>
                  </>
                ) : null}
                <dt className="text-slate-500">Method</dt>
                <dd className="font-medium text-slate-900">{receipt.payment_method}</dd>
                {receipt.payment_reference ? (
                  <>
                    <dt className="text-slate-500">Reference</dt>
                    <dd className="font-medium text-slate-900">{receipt.payment_reference}</dd>
                  </>
                ) : null}
                <dt className="text-slate-500">Paid at</dt>
                <dd className="font-medium text-slate-900">
                  {formatReceiptDateTime(receipt.paid_at)}
                </dd>
                <dt className="text-slate-500">Issued</dt>
                <dd className="font-medium text-slate-900">
                  {formatReceiptDateTime(receipt.issued_at)}
                </dd>
              </dl>
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-1">
            <Button type="button" variant="outline" className="w-fit" onClick={onClose}>
              Close
            </Button>
            <Button type="button" className="w-fit" onClick={handlePrint}>
              Print / save as PDF
            </Button>
          </div>
        </div>
      )}
    </Modal>
  )
}

export default ReceiptViewModal
