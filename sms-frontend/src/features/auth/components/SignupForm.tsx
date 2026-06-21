import { FormLabel, InputField, CheckboxField, Button } from '@/components/ui'
import { FormWrapper } from '@/features/auth/components'
import AppLogo from '@/components/shared/AppLogo'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'
import { signup } from '@/features/auth/services'
import { useAuthStore } from '@/features/auth/store'
import { useMutation } from '@tanstack/react-query'
import { useNavigate, Link } from 'react-router-dom'
import toast from 'react-hot-toast'
import { getApiErrorMessage } from '@/utils'

const SignupForm = () => {
  return (
    <FormWrapper>
      {/* header */}
      <div className="flex justify-center items-center gap-8 flex-col text-center mb-6">
        <AppLogo />
        <div className="">
          <h2 className="font-semibold text-2xl mb-3">Admin sign up</h2>
          <p className="text-lg text-slate-400">Register your school and create an admin account</p>
        </div>
      </div>

      {/* Form */}
      <Form />
    </FormWrapper>
  )
}

export default SignupForm

const schema = z.object({
  school_name: z.string().min(1, { message: 'School name is required' }),
  first_name: z.string().min(1, { message: 'First name is required' }),
  last_name: z.string().min(1, { message: 'Last name is required' }),
  phone_number: z
    .string()
    .min(1, { message: 'Phone number is required' })
    .regex(/^(\+233|0)[0-9]{9}$/, 'Invalid Ghana number'),
  email: z.string().email({ message: 'Invalid email address' }),
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

  const { mutate: signupMutation } = useMutation({
    mutationFn: signup,
  })

  const onSubmit = (data: FormData) => {
    signupMutation(data, {
      onSuccess: () => {
        setVerificationPhone(data.phone_number)
        toast.success('Account created. Please verify your phone number.')
        navigate('/auth/signup/verify-otp')
      },
      onError: (mutationError) => {
        toast.error(getApiErrorMessage(mutationError, 'Unable to create account. Please try again.'))
      },
    })
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      {/* School Name */}
      <div className="space-y-2">
        <FormLabel label="School Name" required />
        <InputField
          placeholder="Enter the name of your school"
          error={errors.school_name?.message}
          {...register('school_name')}
        />
      </div>
      {/* First Name */}
      <div className="space-y-2">
        <FormLabel label="First Name" required />
        <InputField
          placeholder="Enter your first name"
          error={errors.first_name?.message}
          {...register('first_name')}
        />
      </div>
      {/* Last Name */}
      <div className="space-y-2">
        <FormLabel label="Last Name" required />
        <InputField
          placeholder="Enter your last name"
          error={errors.last_name?.message}
          {...register('last_name')}
        />
      </div>
      {/* Phone Number */}
      <div className="space-y-2">
        <FormLabel label="Phone Number" required />
        <InputField
          placeholder="Enter your phone number"
          error={errors.phone_number?.message}
          type="tel"
          {...register('phone_number')}
        />
      </div>
      {/* Email */}
      <div className="space-y-2">
        <FormLabel label="Email" required />
        <InputField
          placeholder="Enter your email"
          type="email"
          error={errors.email?.message}
          {...register('email')}
        />
      </div>
      {/* Accept terms and conditions */}
      <div className="space-y-2">
        <CheckboxField required>Accept terms and conditions</CheckboxField>
      </div>

      <Button type="submit" variant="outline">
        Sign up
      </Button>

      <p className="text-sm text-slate-500 text-center">
        Already have an account?{' '}
        <Link to="/auth/login" className="text-blue-500 hover:text-blue-600">
          Log in
        </Link>
      </p>
    </form>
  )
}
