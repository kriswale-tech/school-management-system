import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import SignupForm from '../components/SignupForm'
import { FormWrapper } from '../components'
import AppLogo from '@/components/shared/AppLogo'
import { getPublicConfig } from '../services'

const SignupPage = () => {
  const configQuery = useQuery({
    queryKey: ['public-config'],
    queryFn: getPublicConfig,
  })

  if (configQuery.isLoading) {
    return (
      <FormWrapper>
        <p className="text-center text-slate-500">Checking registration availability…</p>
      </FormWrapper>
    )
  }

  if (configQuery.data && !configQuery.data.public_school_registration_enabled) {
    return (
      <FormWrapper>
        <div className="mb-6 flex flex-col items-center gap-6 text-center">
          <AppLogo />
          <div>
            <h2 className="mb-3 text-2xl font-semibold">Registration closed</h2>
            <p className="text-lg text-slate-400">
              Public school registration is currently disabled. Contact SCHOOLASST to get your
              school onboarded.
            </p>
          </div>
        </div>
        <p className="text-center text-sm text-slate-500">
          Already have an account?{' '}
          <Link to="/auth/login" className="text-blue-500 hover:text-blue-600">
            Log in
          </Link>
        </p>
      </FormWrapper>
    )
  }

  return (
    <div>
      <SignupForm />
    </div>
  )
}

export default SignupPage
