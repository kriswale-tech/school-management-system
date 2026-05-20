import { FormLabel, InputField, CheckboxField, Button } from '@/components/ui'
import FormWrapper from './FormWrapper'
import AppLogo from '@/components/shared/AppLogo'
import { useForm } from 'react-hook-form'
import { z } from 'zod'
import { zodResolver } from '@hookform/resolvers/zod'

const SignupForm = () => {
  return (
    <FormWrapper>
      {/* header */}
      <div className="flex justify-center items-center gap-8 flex-col text-center mb-6">
        <AppLogo />
        <div className="">
          <h2 className="font-semibold text-3xl mb-3">Admin sign up</h2>
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
  name: z.string().min(1, { message: 'Name is required' }),
  phone_number: z
    .string()
    .min(1, { message: 'Phone number is required' })
    .regex(/^(\+233|0)[0-9]{9}$/, 'Invalid Ghana number'),
  email: z.string().email({ message: 'Invalid email address' }),
})

type FormData = z.infer<typeof schema>

const Form = () => {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormData>({
    resolver: zodResolver(schema),
  })

  const onSubmit = (data: FormData) => {
    console.log(data)
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
      {/* Name */}
      <div className="space-y-2">
        <FormLabel label="Name" required />
        <InputField
          placeholder="Enter your name"
          error={errors.name?.message}
          {...register('name')}
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
    </form>
  )
}
