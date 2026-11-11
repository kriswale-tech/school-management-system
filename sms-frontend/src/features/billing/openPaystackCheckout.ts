import PaystackPop from '@paystack/inline-js'
import type { SaasPayment } from './types'

type CheckoutHandlers = {
  onSuccess: (reference: string) => void | Promise<void>
  onCancel?: () => void
  onError?: (message: string) => void
}

export function openPaystackCheckout(payment: SaasPayment, handlers: CheckoutHandlers) {
  const accessCode = payment.access_code?.trim()
  if (!accessCode) {
    if (payment.authorization_url) {
      window.location.assign(payment.authorization_url)
      return
    }
    handlers.onError?.('Paystack checkout could not be opened.')
    return
  }

  const popup = new PaystackPop()
  popup.resumeTransaction(accessCode, {
    onSuccess: (transaction) => {
      void handlers.onSuccess(transaction.reference || payment.reference)
    },
    onCancel: () => handlers.onCancel?.(),
    onError: (error) => {
      handlers.onError?.(error.message || 'Payment could not be completed.')
    },
  })
}
