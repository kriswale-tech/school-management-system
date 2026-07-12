import { useState, type FormEvent } from 'react'
import { FormWrapper } from '@/features/auth/components'
import { AppLogo } from '@/components/shared'
import { Button, OTPInput } from '@/components/ui'
import { mergeClasses } from '@/utils'

export interface OTPFormProps {
  phoneNumber: string
  title?: string
  error?: string
  onOtpChange?: (_value: string) => void
  onSubmit: (_otp: string) => void
  isSubmitting?: boolean
  submitLabel?: string
  submittingLabel?: string
  onResend: () => void
  isResending?: boolean
  resendCooldownSeconds: number
}

const OTPForm = ({
  phoneNumber,
  title = 'Verification',
  error,
  onOtpChange,
  onSubmit,
  isSubmitting = false,
  submitLabel = 'Verify OTP',
  submittingLabel = 'Verifying...',
  onResend,
  isResending = false,
  resendCooldownSeconds,
}: OTPFormProps) => {
  const [otp, setOtp] = useState('')

  const handleOtpChange = (value: string) => {
    setOtp(value)
    onOtpChange?.(value)
  }

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    onSubmit(otp)
  }

  return (
    <FormWrapper>
      <form
        onSubmit={handleSubmit}
        className="flex justify-center items-center gap-8 flex-col text-center mb-6 max-w-lg mx-auto"
      >
        <AppLogo />
        <div>
          <h2 className="font-semibold text-2xl mb-3">{title}</h2>
          <p className="text-lg text-slate-500 text-center">
            We've sent a 6 digit code to <span className="font-semibold">{phoneNumber}.</span>
            <br />
            Enter below to continue
          </p>
        </div>

        <OTPInput value={otp} onChange={handleOtpChange} error={error} />

        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? submittingLabel : submitLabel}
        </Button>

        <div className="text-sm text-slate-500 text-center">
          <span>Didn't receive the code? </span>
          <button
            type="button"
            disabled={resendCooldownSeconds > 0 || isResending}
            onClick={onResend}
            className={mergeClasses(
              'text-blue-500 hover:text-blue-600 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:text-blue-500',
            )}
          >
            {isResending
              ? 'Sending...'
              : resendCooldownSeconds > 0
                ? `Resend OTP in ${resendCooldownSeconds}s`
                : 'Resend OTP'}
          </button>
        </div>
      </form>
    </FormWrapper>
  )
}

export default OTPForm
