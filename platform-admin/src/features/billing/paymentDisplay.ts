import type { SaasPayment } from './types'

export function paymentForLabel(payment: SaasPayment) {
  if (payment.purpose === 'topup') {
    const name = payment.package_name || 'Credit top-up'
    const credits = payment.topup_credits
    const channel = (payment.topup_channel || '').toUpperCase()
    if (credits && channel) {
      return `${name} · ${credits.toLocaleString()} ${channel} credits`
    }
    return payment.label || name
  }
  return payment.invoice_notes || payment.label || 'Subscription invoice'
}

export function paymentKindLabel(payment: SaasPayment) {
  if (payment.purpose_label) return payment.purpose_label
  return payment.purpose === 'topup' ? 'Top-up' : 'Invoice'
}

export function paymentProviderLabel(provider: string) {
  if (provider === 'manual') return 'Recorded here'
  if (provider === 'paystack') return 'Paystack'
  return provider || '—'
}
