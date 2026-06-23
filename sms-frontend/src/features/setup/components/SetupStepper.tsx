import { Link } from 'react-router-dom'
import { mergeClasses } from '@/utils'

export type SetupStep = {
  label: string
  path: string
  completed: boolean
}

export type SetupStepperProps = {
  currentStep: number
  steps: SetupStep[]
}

const SetupStepper = ({ currentStep, steps }: SetupStepperProps) => {
  return (
    <div className="flex flex-wrap items-center gap-6">
      {steps.map((step, index) => (
        <StepperItem
          key={step.path}
          number={index + 1}
          label={step.label}
          path={step.path}
          completed={step.completed}
          isCurrent={index + 1 === currentStep}
        />
      ))}
    </div>
  )
}

export default SetupStepper

type StepperItemProps = {
  label: string
  number: number
  path: string
  completed: boolean
  isCurrent: boolean
}

const StepperItem = ({ label, number, path, completed, isCurrent }: StepperItemProps) => {
  const isFaded = !completed && !isCurrent
  const canNavigate = completed && !isCurrent

  const content = (
    <>
      <div
        className={mergeClasses(
          'flex size-8 items-center justify-center rounded-full border ',
          isFaded ? 'border-slate-300 text-slate-400' : 'border-slate-600 text-slate-700',
          isCurrent && 'border-slate-900 text-slate-900',
        )}
      >
        {number}
      </div>
      <p
        className={mergeClasses(
          isFaded ? 'text-slate-400' : 'text-slate-700',
          isCurrent && 'text-slate-900',
        )}
      >
        {label}
      </p>
    </>
  )

  if (canNavigate) {
    return (
      <Link to={path} className="flex items-center gap-2 transition-opacity hover:opacity-80">
        {content}
      </Link>
    )
  }

  return (
    <div
      className={mergeClasses('flex items-center gap-2', isFaded && 'opacity-50')}
      aria-current={isCurrent ? 'step' : undefined}
    >
      {content}
    </div>
  )
}
