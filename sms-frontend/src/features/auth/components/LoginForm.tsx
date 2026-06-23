import { FormLabel, InputField, Button } from '@/components/ui'
import { FormWrapper } from '@/features/auth/components'
import AppLogo from '@/components/shared/AppLogo'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { login } from '@/features/auth/services'
import { useAuthStore } from '@/features/auth/store'
import { useMutation } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { getApiErrorMessage } from '@/utils'

const LoginForm = () => {
  return (
    <FormWrapper>
      <div className="flex justify-center items-center gap-8 flex-col text-center mb-6">
        <AppLogo />
        <div>
          <h2 className="font-semibold text-2xl mb-3">Login to your account</h2>
          <p className="text-lg text-slate-400">
            Enter your phone number to continue. We'll send you a one time verification code (OTP)
            to securely log you in.
          </p>
        </div>
      </div>

      <Form />
    </FormWrapper>
  )
}

export default LoginForm

const schema = z.object({
  phone_number: z
    .string()
    .min(1, { message: 'Phone number is required' })
    .regex(/^(\+233|0)[0-9]{9}$/, 'Invalid Ghana number'),
})

type FormData = z.infer<typeof schema>

const Form = () => {
  const navigate = useNavigate()
  const setVerificationPhone = useAuthStore((state) => state.setVerificationPhone)
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
  })

  const { mutate: loginMutation, isPending } = useMutation({
    mutationFn: login,
  })

  const onSubmit = (data: FormData) => {
    loginMutation(
      { phone_number: data.phone_number },
      {
        onSuccess: () => {
          setVerificationPhone(data.phone_number)
          toast.success('Verification code sent to your phone.')
          navigate('/auth/login/verify-otp')
        },
        onError: (mutationError) => {
          toast.error(getApiErrorMessage(mutationError, 'Unable to log in. Please try again.'))
        },
      },
    )
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      <div className="space-y-2">
        <FormLabel label="Phone Number" required />
        <InputField
          placeholder="Enter your phone number"
          error={errors.phone_number?.message}
          type="tel"
          {...register('phone_number')}
        />
      </div>

      <Button type="submit" disabled={isPending}>
        {isPending ? 'Sending code...' : 'Continue'}
      </Button>
    </form>
  )
}
