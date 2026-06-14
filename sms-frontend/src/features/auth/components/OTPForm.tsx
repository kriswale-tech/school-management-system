import { useState, type FormEvent } from 'react'
import { FormWrapper } from '@/features/auth/components'
import { AppLogo } from '@/components/shared'
import { Button, OTPInput } from '@/components/ui'

interface OTPFormProps {
  phoneNumber: string
  title?: string
}

const OTPForm = ({ phoneNumber, title = 'Verification' }: OTPFormProps) => {
  const [otp, setOtp] = useState('')
  const [error, setError] = useState('')

  const handleOtpChange = (value: string) => {
    setOtp(value)
    if (error) setError('')
  }

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    if (!/^\d{6}$/.test(otp)) {
      setError('Please enter the complete 6-digit code')
      return
    }

    setError('')
    // TODO: verify OTP with backend
  }

  return (
    <FormWrapper>
      <form
        onSubmit={handleSubmit}
        className="flex justify-center items-center gap-8 flex-col text-center mb-6 max-w-lg mx-auto"
      >
        <AppLogo />
        <div className="">
          <h2 className="font-semibold text-2xl mb-3">{title}</h2>
          <p className="text-lg text-slate-500 text-center">
            We've sent a 6 digit code to <span className="font-semibold">{phoneNumber}.</span>
            <br />
            Enter below to continue
          </p>
        </div>

        <OTPInput value={otp} onChange={handleOtpChange} error={error} />

        <Button type="submit">Verify OTP</Button>

        <div className="text-sm text-slate-500 text-center">
          <span className="">Didn't receive the code? </span>
          <button type="button" className="text-blue-500 hover:text-blue-600">
            Resend OTP
          </button>
        </div>
      </form>
    </FormWrapper>
  )
}

export default OTPForm
