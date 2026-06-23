import { Outlet, useLocation } from 'react-router-dom'
import { AppToaster, AuthLoading } from '@/components/shared'
import { useAuth } from '@/features/auth/hooks'
import NavBar from '@/components/shared/NavBar'
import SetupStepper from '@/features/setup/components/SetupStepper'
import { setupSteps } from '@/features/setup/constants'

const SetupLayout = () => {
  const location = useLocation()
  const { isReady, isAuthenticated } = useAuth({ requireAuth: true })

  const currentStepIndex = setupSteps.findIndex((step) => location.pathname.startsWith(step.path))
  const currentStep = currentStepIndex === -1 ? 1 : currentStepIndex + 1

  const steps = setupSteps.map((step, index) => ({
    ...step,
    completed: index + 1 < currentStep,
  }))

  if (!isReady || !isAuthenticated) {
    return (
      <>
        <AppToaster />
        <AuthLoading />
      </>
    )
  }

  return (
    <>
      <AppToaster />
      <div>
        {/* Navbar */}
        <NavBar />

        <main className="mx-auto max-w-7xl px-4 space-y-6 mt-8">
          <header className="border-b border-slate-200 pb-6">
            <h1 className="text-4xl font-semibold">Setup Completion</h1>
            <p className="text-lg text-slate-500 mt-2">
              Complete initial configuration to activate your school
            </p>
          </header>

          {/* Stepper component */}
          <div className="mx-auto">
            <SetupStepper currentStep={currentStep} steps={steps} />
          </div>

          {/* Pages */}
          <div className="">
            <Outlet />
          </div>
        </main>
      </div>
    </>
  )
}

export default SetupLayout
