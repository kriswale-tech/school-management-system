declare module '@paystack/inline-js' {
  export type PaystackTransaction = {
    reference?: string
    status?: string
    message?: string
    trans?: string
    transaction?: string
    trxref?: string
  }

  export type PaystackPopupError = {
    message?: string
  }

  export default class PaystackPop {
    resumeTransaction(
      accessCode: string,
      callbacks?: {
        onSuccess?: (transaction: PaystackTransaction) => void
        onCancel?: () => void
        onError?: (error: PaystackPopupError) => void
      },
    ): void
  }
}
