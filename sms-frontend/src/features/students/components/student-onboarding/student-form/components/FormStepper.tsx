import { mergeClasses } from '@/utils'
import type { StudentFormStepId } from '../types'
import { STUDENT_FORM_STEPS } from '../constants'

type FormStepperProps = {
  currentStepId: StudentFormStepId
  completedStepIds: StudentFormStepId[]
  onStepClick: (stepId: StudentFormStepId) => void
}

const FormStepper = ({ currentStepId, completedStepIds, onStepClick }: FormStepperProps) => {
  return (
    <div className="flex flex-wrap items-center gap-6 overflow-x-auto pb-1">
      {STUDENT_FORM_STEPS.map((step, index) => {
        const isCurrent = step.id === currentStepId
        const isCompleted = completedStepIds.includes(step.id)
        const canNavigate = isCompleted && !isCurrent
        const isFaded = !isCompleted && !isCurrent

        const content = (
          <>
            <div
              className={mergeClasses(
                'flex size-8 shrink-0 items-center justify-center rounded-full border text-sm',
                isFaded ? 'border-slate-400 text-slate-600' : 'border-slate-600 text-slate-700',
                isCurrent && 'border-slate-900 text-slate-900',
                isCompleted && !isCurrent && 'border-slate-900 bg-slate-900 text-white',
              )}
            >
              {index + 1}
            </div>
            <p
              className={mergeClasses(
                'whitespace-nowrap text-sm',
                isFaded ? 'text-slate-600' : 'text-slate-700',
                isCurrent && 'text-slate-900 font-medium',
              )}
            >
              {step.label}
            </p>
          </>
        )

        if (canNavigate) {
          return (
            <button
              key={step.id}
              type="button"
              onClick={() => onStepClick(step.id)}
              className="flex shrink-0 items-center gap-2 transition-opacity hover:opacity-80"
            >
              {content}
            </button>
          )
        }

        return (
          <div
            key={step.id}
            className={mergeClasses('flex shrink-0 items-center gap-2', isFaded && 'opacity-50')}
            aria-current={isCurrent ? 'step' : undefined}
          >
            {content}
          </div>
        )
      })}
    </div>
  )
}

export default FormStepper
