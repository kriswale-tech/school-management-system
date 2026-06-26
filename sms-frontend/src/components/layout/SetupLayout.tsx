import { useEffect } from 'react'
import { Outlet, useLocation, useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { AppToaster, AuthLoading } from '@/components/shared'
import { useAuth } from '@/features/auth/hooks'
import NavBar from '@/components/shared/NavBar'
import SetupStepper from '@/features/setup/components/SetupStepper'
import { getSetup } from '@/features/setup/services'

const SetupLayout = () => {
  const location = useLocation()
  const navigate = useNavigate()
  const { isReady, isAuthenticated } = useAuth({ requireAuth: true })

  const { data: setup, isLoading } = useQuery({
    queryKey: ['setup'],
    queryFn: getSetup,
    enabled: isReady && isAuthenticated,
  })

  const urlStep = location.pathname.replace(/^\/setup\/?/, '').split('/')[0] || null

  useEffect(() => {
    if (!setup) return

    const validSteps = setup.steps.map((step) => step.step)

    if (!urlStep || !validSteps.includes(urlStep)) {
      navigate(`/setup/${setup.current_step}`, { replace: true })
    }
  }, [setup, urlStep, navigate])

  if (!isReady || !isAuthenticated || isLoading || !setup) {
    return (
      <>
        <AppToaster />
        <AuthLoading />
      </>
    )
  }

  const currentStep =
    urlStep && setup.steps.some((step) => step.step === urlStep) ? urlStep : setup.current_step

  const steps = setup.steps.map((step) => ({
    label: step.name,
    step: step.step,
    path: `/setup/${step.step}`,
    completed: step.completed,
  }))

  return (
    <>
      <AppToaster />
      <div>
        <NavBar />

        <main className="mx-auto max-w-7xl px-6 space-y-6 mt-8">
          <header className="border-b border-slate-200 pb-6">
            <h1 className="text-4xl font-semibold">Setup Completion</h1>
            <p className="text-lg text-slate-500 mt-2">
              Complete initial configuration to activate your school
            </p>
          </header>

          <div className="mx-auto">
            <SetupStepper
              currentStep={currentStep}
              workflowStep={setup.current_step}
              steps={steps}
            />
          </div>

          <div className="my-10!">
            <Outlet context={setup} />
          </div>
        </main>
      </div>
    </>
  )
}

export default SetupLayout
