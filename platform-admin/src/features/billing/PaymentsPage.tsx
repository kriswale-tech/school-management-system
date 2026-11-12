import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { isAxiosError } from 'axios'
import toast from 'react-hot-toast'
import { formatDateTime } from '@/lib/dates'
import { ListPager } from './ListPager'
import { StatusBadge } from './StatusBadge'
import { paymentForLabel, paymentKindLabel, paymentProviderLabel } from './paymentDisplay'
import { listPayments, verifyPayment } from './services'
import type { SaasPayment } from './types'

function formatGhs(value: string) {
  return `GH₵ ${Number(value).toLocaleString('en-GH', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`
}

function errorMessage(error: unknown) {
  if (!isAxiosError(error)) return 'Request failed'
  const data = error.response?.data
  if (!data || typeof data !== 'object') return 'Request failed'
  const record = data as Record<string, unknown>
  if (typeof record.detail === 'string' && record.detail) return record.detail
  return 'Request failed'
}

export default function PaymentsPage() {
  const queryClient = useQueryClient()
  const [pendingVerify, setPendingVerify] = useState<SaasPayment | null>(null)
  const [page, setPage] = useState(1)
  const paymentsQuery = useQuery({
    queryKey: ['platform-billing-payments', page],
    queryFn: () => listPayments({ page }),
  })
  const verifyMutation = useMutation({
    mutationFn: (paymentId: string) => verifyPayment(paymentId),
    onSuccess: () => {
      toast.success('Payment verified')
      setPendingVerify(null)
      void queryClient.invalidateQueries({ queryKey: ['platform-billing-payments'] })
      void queryClient.invalidateQueries({ queryKey: ['platform-school-payments'] })
      void queryClient.invalidateQueries({ queryKey: ['platform-school-invoices'] })
      void queryClient.invalidateQueries({ queryKey: ['platform-school-credits'] })
      void queryClient.invalidateQueries({ queryKey: ['platform-school-finance'] })
      void queryClient.invalidateQueries({ queryKey: ['platform-school-subscription'] })
      void queryClient.invalidateQueries({ queryKey: ['platform-school-audit'] })
    },
    onError: (error) => toast.error(errorMessage(error)),
  })

  return (
    <div>
      <div className="mb-8">
        <h1 className="font-[family-name:var(--font-display)] text-3xl font-semibold">
          Payments
        </h1>
        <p className="mt-2 text-sm text-[var(--color-ink)]/70">
          SaaS Paystack checkouts for renewals, upgrades, and communication top-ups.
        </p>
      </div>

      {paymentsQuery.isLoading && (
        <p className="text-sm text-[var(--color-ink)]/60">Loading…</p>
      )}
      {paymentsQuery.isError && (
        <p className="text-sm text-red-700">Could not load payments.</p>
      )}

      <div className="overflow-hidden rounded-2xl border border-[var(--color-line)] bg-white">
        <table className="min-w-full text-left text-sm">
          <thead className="border-b border-[var(--color-line)] bg-[var(--color-accent-soft)]/40 text-[var(--color-ink)]/70">
            <tr>
              <th className="px-4 py-3 font-medium">School</th>
              <th className="px-4 py-3 font-medium">Amount</th>
              <th className="px-4 py-3 font-medium">For</th>
              <th className="px-4 py-3 font-medium">Provider</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Reference</th>
              <th className="px-4 py-3 font-medium">Paystack id</th>
              <th className="px-4 py-3 font-medium">When</th>
              <th className="px-4 py-3 font-medium" />
            </tr>
          </thead>
          <tbody>
            {(paymentsQuery.data?.results ?? []).length === 0 && !paymentsQuery.isLoading && (
              <tr>
                <td colSpan={9} className="px-4 py-6 text-[var(--color-ink)]/60">
                  No SaaS payments yet.
                </td>
              </tr>
            )}
            {(paymentsQuery.data?.results ?? []).map((payment) => (
              <tr key={payment.id} className="border-b border-[var(--color-line)] last:border-0">
                <td className="px-4 py-3">
                  <Link
                    to={`/schools/${payment.school}`}
                    className="font-medium text-[var(--color-accent)] hover:underline"
                  >
                    {payment.school_name || payment.school}
                  </Link>
                </td>
                <td className="px-4 py-3">{formatGhs(payment.amount_ghs)}</td>
                <td className="px-4 py-3">
                  <p className="font-medium">{paymentKindLabel(payment)}</p>
                  <p className="max-w-xs text-[var(--color-ink)]/65">{paymentForLabel(payment)}</p>
                </td>
                <td className="px-4 py-3">{paymentProviderLabel(payment.provider)}</td>
                <td className="px-4 py-3">
                  <StatusBadge status={payment.status} />
                </td>
                <td className="px-4 py-3 font-mono text-xs">{payment.reference}</td>
                <td className="px-4 py-3 font-mono text-xs">
                  {payment.provider_transaction_id || '—'}
                </td>
                <td className="px-4 py-3 text-[var(--color-ink)]/60">
                  {formatDateTime(payment.paid_at || payment.created_at)}
                </td>
                <td className="px-4 py-3 text-right">
                  {payment.status === 'pending' && payment.provider === 'paystack' && (
                    <button
                      type="button"
                      className="rounded-full border border-[var(--color-line)] px-3 py-1 text-xs font-semibold"
                      disabled={verifyMutation.isPending}
                      onClick={() => setPendingVerify(payment)}
                    >
                      Verify
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <ListPager count={paymentsQuery.data?.count ?? 0} page={page} onPage={setPage} />

      {pendingVerify && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
          <div className="w-full max-w-md rounded-2xl border border-[var(--color-line)] bg-white p-5 shadow-lg">
            <h2 className="font-[family-name:var(--font-display)] text-lg font-semibold">
              Verify this payment?
            </h2>
            <p className="mt-3 text-sm text-[var(--color-ink)]/70">
              Paystack will be checked for {pendingVerify.reference}. If Paystack confirms it, the
              invoice is completed. If not, the payment stays as it is.
            </p>
            <div className="mt-5 flex justify-end gap-2">
              <button
                type="button"
                className="rounded-full border border-[var(--color-line)] px-4 py-2 text-sm font-semibold"
                disabled={verifyMutation.isPending}
                onClick={() => setPendingVerify(null)}
              >
                Back
              </button>
              <button
                type="button"
                className="rounded-full bg-[var(--color-ink)] px-4 py-2 text-sm font-semibold text-white"
                disabled={verifyMutation.isPending}
                onClick={() => verifyMutation.mutate(pendingVerify.id)}
              >
                {verifyMutation.isPending ? 'Checking…' : 'Verify'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
