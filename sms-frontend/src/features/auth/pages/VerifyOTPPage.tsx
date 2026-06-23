import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { useMutation } from '@tanstack/react-query'
import { Navigate, useLocation } from 'react-router-dom'
import { OTPForm } from '../components'
import { verifyOTP, verifyLoginOTP, getUser, resendOTP, resendLoginOTP } from '../services'
import { useAuthStore } from '../store'
import { getApiErrorMessage } from '@/utils'

const RESEND_COOLDOWN_SECONDS = 60

const VerifyOTPPage = () => {
  const location = useLocation()
  const isLoginFlow = location.pathname.includes('/login/')
  const redirectTo = isLoginFlow ? '/auth/login' : '/auth/signup'
  const title = isLoginFlow ? 'Login verification' : 'Admin verification'
  const successMessage = isLoginFlow ? 'Logged in successfully' : 'Account verified successfully'

  const verificationPhone = useAuthStore((state) => state.verificationPhone)
  const setUser = useAuthStore((state) => state.setUser)
  const clearVerificationPhone = useAuthStore((state) => state.clearVerificationPhone)

  const [error, setError] = useState('')
  const [resendCooldownSeconds, setResendCooldownSeconds] = useState(RESEND_COOLDOWN_SECONDS)

  useEffect(() => {
    if (resendCooldownSeconds <= 0) return

    const timer = setTimeout(() => {
      setResendCooldownSeconds((seconds) => seconds - 1)
    }, 1000)

    return () => clearTimeout(timer)
  }, [resendCooldownSeconds])

  const { mutate: verifyOtpMutation, isPending: isVerifying } = useMutation({
    mutationFn: async (otp: string) => {
      const verify = isLoginFlow ? verifyLoginOTP : verifyOTP
      await verify({ phone_number: verificationPhone!, otp })
      return getUser()
    },
  })

  const { mutate: resendOtpMutation, isPending: isResending } = useMutation({
    mutationFn: () => {
      const resend = isLoginFlow ? resendLoginOTP : resendOTP
      return resend({ phone_number: verificationPhone! })
    },
    onSuccess: () => {
      setResendCooldownSeconds(RESEND_COOLDOWN_SECONDS)
      toast.success('A new verification code has been sent')
    },
    onError: (mutationError) => {
      toast.error(getApiErrorMessage(mutationError, 'Unable to resend code. Please try again.'))
    },
  })

  if (!verificationPhone) {
    return <Navigate to={redirectTo} replace />
  }

  const handleOtpChange = () => {
    if (error) setError('')
  }

  const handleSubmit = (otp: string) => {
    if (!/^\d{6}$/.test(otp)) {
      setError('Please enter the complete 6-digit code')
      return
    }

    verifyOtpMutation(otp, {
      onSuccess: (user) => {
        setUser(user)
        clearVerificationPhone()
        toast.success(successMessage)
      },
      onError: (mutationError) => {
        toast.error(getApiErrorMessage(mutationError, 'Unable to verify code. Please try again.'))
      },
    })
  }

  const handleResend = () => {
    resendOtpMutation()
  }

  return (
    <OTPForm
      phoneNumber={verificationPhone}
      title={title}
      error={error}
      onOtpChange={handleOtpChange}
      onSubmit={handleSubmit}
      isSubmitting={isVerifying}
      onResend={handleResend}
      isResending={isResending}
      resendCooldownSeconds={resendCooldownSeconds}
    />
  )
}

export default VerifyOTPPage
