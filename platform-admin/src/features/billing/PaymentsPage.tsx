import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { listPayments } from './services'

function formatGhs(value: string) {
  return `GH₵ ${Number(value).toLocaleString('en-GH', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`
}

export default function PaymentsPage() {
  const paymentsQuery = useQuery({
    queryKey: ['platform-billing-payments'],
    queryFn: () => listPayments(),
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
              <th className="px-4 py-3 font-medium">Purpose</th>
              <th className="px-4 py-3 font-medium">Amount</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Reference</th>
              <th className="px-4 py-3 font-medium">When</th>
            </tr>
          </thead>
          <tbody>
            {(paymentsQuery.data?.results ?? []).length === 0 && !paymentsQuery.isLoading && (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-[var(--color-ink)]/60">
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
                <td className="px-4 py-3 capitalize">{payment.purpose}</td>
                <td className="px-4 py-3">{formatGhs(payment.amount_ghs)}</td>
                <td className="px-4 py-3 capitalize">{payment.status}</td>
                <td className="px-4 py-3 font-mono text-xs">{payment.reference}</td>
                <td className="px-4 py-3 text-[var(--color-ink)]/60">
                  {new Date(payment.paid_at || payment.created_at).toLocaleString('en-GB')}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
