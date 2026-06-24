import { useCallback, useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { Icon } from '@iconify/react'
import { mergeClasses } from '@/utils'

export type SetupStep = {
  label: string
  step: string
  path: string
  completed: boolean
}

export type SetupStepperProps = {
  currentStep: string
  workflowStep: string
  steps: SetupStep[]
}

const SetupStepper = ({ currentStep, workflowStep, steps }: SetupStepperProps) => {
  const scrollRef = useRef<HTMLDivElement>(null)
  const [canScrollLeft, setCanScrollLeft] = useState(false)
  const [canScrollRight, setCanScrollRight] = useState(false)

  const updateScrollState = useCallback(() => {
    const element = scrollRef.current
    if (!element) return

    const { scrollLeft, scrollWidth, clientWidth } = element
    setCanScrollLeft(scrollLeft > 0)
    setCanScrollRight(scrollLeft + clientWidth < scrollWidth - 1)
  }, [])

  useEffect(() => {
    const element = scrollRef.current
    if (!element) return

    updateScrollState()
    element.addEventListener('scroll', updateScrollState, { passive: true })

    const resizeObserver = new ResizeObserver(updateScrollState)
    resizeObserver.observe(element)

    return () => {
      element.removeEventListener('scroll', updateScrollState)
      resizeObserver.disconnect()
    }
  }, [steps, updateScrollState])

  useEffect(() => {
    const currentItem = scrollRef.current?.querySelector('[aria-current="step"]')
    currentItem?.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' })
  }, [currentStep, steps])

  const scroll = (direction: 'left' | 'right') => {
    scrollRef.current?.scrollBy({
      left: direction === 'left' ? -220 : 220,
      behavior: 'smooth',
    })
  }

  return (
    <div className="relative">
      {canScrollLeft ? (
        <>
          <div className="pointer-events-none absolute inset-y-0 left-0 z-10 w-10 bg-linear-to-r from-white to-transparent" />
          <button
            type="button"
            onClick={() => scroll('left')}
            aria-label="Scroll steps left"
            className="absolute left-0 top-1/2 z-20 flex size-8 -translate-y-1/2 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-600 shadow-sm"
          >
            <Icon icon="mdi:chevron-left" className="text-xl" />
          </button>
        </>
      ) : null}

      {canScrollRight ? (
        <>
          <div className="pointer-events-none absolute inset-y-0 right-0 z-10 w-10 bg-linear-to-l from-white to-transparent" />
          <button
            type="button"
            onClick={() => scroll('right')}
            aria-label="Scroll steps right"
            className="absolute right-0 top-1/2 z-20 flex size-8 -translate-y-1/2 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-600 shadow-sm"
          >
            <Icon icon="mdi:chevron-right" className="text-xl" />
          </button>
        </>
      ) : null}

      <div
        ref={scrollRef}
        className={mergeClasses(
          'flex items-center gap-6 overflow-x-auto scroll-smooth',
          '[scrollbar-width:none] [-ms-overflow-style:none] [&::-webkit-scrollbar]:hidden',
          canScrollLeft && 'pl-8',
          canScrollRight && 'pr-8',
        )}
      >
        {steps.map((step, index) => (
          <StepperItem
            key={step.step}
            number={index + 1}
            label={step.label}
            path={step.path}
            completed={step.completed}
            isCurrent={step.step === currentStep}
            isWorkflowCurrent={step.step === workflowStep}
          />
        ))}
      </div>
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
  isWorkflowCurrent: boolean
}

const StepperItem = ({
  label,
  number,
  path,
  completed,
  isCurrent,
  isWorkflowCurrent,
}: StepperItemProps) => {
  const isActive = isCurrent || isWorkflowCurrent
  const isFaded = !completed && !isActive
  const canNavigate = (completed || isWorkflowCurrent) && !isCurrent

  const content = (
    <>
      <div
        className={mergeClasses(
          'flex size-8 shrink-0 items-center justify-center rounded-full border',
          isFaded ? 'border-slate-400 text-slate-600' : 'border-slate-600 text-slate-700',
          isCurrent && 'border-slate-900 text-slate-900',
        )}
      >
        {number}
      </div>
      <p
        className={mergeClasses(
          'whitespace-nowrap',
          isFaded ? 'text-slate-600' : 'text-slate-700',
          isCurrent && 'text-slate-900',
        )}
      >
        {label}
      </p>
    </>
  )

  if (canNavigate) {
    return (
      <Link
        to={path}
        className="flex shrink-0 items-center gap-2 transition-opacity hover:opacity-80"
      >
        {content}
      </Link>
    )
  }

  return (
    <div
      className={mergeClasses('flex shrink-0 items-center gap-2', isFaded && 'opacity-50')}
      aria-current={isCurrent ? 'step' : undefined}
    >
      {content}
    </div>
  )
}
