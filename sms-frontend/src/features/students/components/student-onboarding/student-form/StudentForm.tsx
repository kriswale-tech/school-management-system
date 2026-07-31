import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { useFieldArray, useForm, type Resolver } from 'react-hook-form'
import toast from 'react-hot-toast'
import { ConfirmDialog } from '@/components/shared'
import { Button } from '@/components/ui'
import type { StudentOnboardPayload } from '@/features/students/types'
import { getApiErrorMessage } from '@/utils'
import type { z } from 'zod'
import { onboardStudent } from '../../../services'
import FormStepper from './components/FormStepper'
import { DEFAULT_STUDENT_FORM_VALUES, STUDENT_FORM_STEPS } from './constants'
import { studentFormSchema } from './schemas'
import BasicDetailsStep from './steps/BasicDetailsStep'
import ClassPlacementStep from './steps/ClassPlacementStep'
import GuardianInfoStep from './steps/GuardianInfoStep'
import type { StudentFormStepId, StudentFormValues } from './types'

type ValidatedStudentForm = z.infer<typeof studentFormSchema>

const toOnboardPayload = (values: ValidatedStudentForm): StudentOnboardPayload => ({
  first_name: values.first_name,
  last_name: values.last_name,
  other_names: values.other_names,
  gender: values.gender,
  date_of_birth: values.date_of_birth,
  admission_date: values.admission_date,
  stream_id: values.stream_id,
  is_new_student: values.is_new_student,
  guardians: values.guardians.map((guardian) => {
    if (guardian.mode === 'existing') {
      return {
        parent_id: guardian.parent_id,
        relationship: guardian.relationship,
      }
    }
    return {
      name: guardian.name,
      phone_number: guardian.phone_number,
      email: guardian.email,
      relationship: guardian.relationship,
    }
  }),
})

const StudentForm = () => {
  const queryClient = useQueryClient()
  const [currentStepIndex, setCurrentStepIndex] = useState(0)
  const [completedStepIds, setCompletedStepIds] = useState<StudentFormStepId[]>([])
  const [confirmOpen, setConfirmOpen] = useState(false)

  const {
    register,
    control,
    trigger,
    handleSubmit,
    reset,
    setValue,
    formState: { errors },
  } = useForm<StudentFormValues, unknown, ValidatedStudentForm>({
    resolver: zodResolver(studentFormSchema) as Resolver<
      StudentFormValues,
      unknown,
      ValidatedStudentForm
    >,
    defaultValues: DEFAULT_STUDENT_FORM_VALUES,
    mode: 'onSubmit',
  })

  const guardiansFieldArray = useFieldArray({
    control,
    name: 'guardians',
  })

  const { mutate: submitOnboard, isPending } = useMutation({
    mutationFn: onboardStudent,
    onSuccess: async () => {
      setConfirmOpen(false)
      toast.success('Student onboarded successfully')
      await queryClient.invalidateQueries({ queryKey: ['students'] })
      await queryClient.invalidateQueries({ queryKey: ['parents'] })
      reset(DEFAULT_STUDENT_FORM_VALUES)
      setCurrentStepIndex(0)
      setCompletedStepIds([])
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, 'Unable to onboard student'))
    },
  })

  const currentStep = STUDENT_FORM_STEPS[currentStepIndex]
  const isFirstStep = currentStepIndex === 0
  const isLastStep = currentStepIndex === STUDENT_FORM_STEPS.length - 1

  const markStepCompleted = (stepId: StudentFormStepId) => {
    setCompletedStepIds((prev) => (prev.includes(stepId) ? prev : [...prev, stepId]))
  }

  const goToStep = (stepId: StudentFormStepId) => {
    const index = STUDENT_FORM_STEPS.findIndex((step) => step.id === stepId)
    if (index >= 0) setCurrentStepIndex(index)
  }

  const onValidSubmit = (values: ValidatedStudentForm) => {
    submitOnboard(toOnboardPayload(values))
  }

  const handleNext = async () => {
    const isValid = await trigger(currentStep.fields)
    if (!isValid) return

    markStepCompleted(currentStep.id)

    if (isLastStep) {
      setConfirmOpen(true)
      return
    }

    setCurrentStepIndex((index) => Math.min(index + 1, STUDENT_FORM_STEPS.length - 1))
  }

  const handleConfirmComplete = () => {
    void handleSubmit(onValidSubmit)()
  }

  const handlePrevious = () => {
    setCurrentStepIndex((index) => Math.max(index - 1, 0))
  }

  return (
    <div className="space-y-6">
      <FormStepper
        currentStepId={currentStep.id}
        completedStepIds={completedStepIds}
        onStepClick={goToStep}
      />

      <div>
        {currentStep.id === 'basic' ? (
          <BasicDetailsStep register={register} control={control} errors={errors} />
        ) : null}
        {currentStep.id === 'guardian' ? (
          <GuardianInfoStep
            register={register}
            control={control}
            setValue={setValue}
            errors={errors}
            guardiansFieldArray={guardiansFieldArray}
          />
        ) : null}
        {currentStep.id === 'placement' ? (
          <ClassPlacementStep control={control} errors={errors} />
        ) : null}
      </div>

      <div className="grid grid-cols-2 gap-3 pt-2">
        <Button type="button" variant="outline" onClick={handlePrevious} disabled={isFirstStep || isPending}>
          Previous
        </Button>
        <Button type="button" onClick={() => void handleNext()} loading={isPending}>
          {isLastStep ? 'Complete' : 'Next'}
        </Button>
      </div>

      <ConfirmDialog
        open={confirmOpen}
        title="Review student details"
        message="Please confirm that all student information is correct before completing onboarding."
        confirmLabel="Complete"
        onClose={() => setConfirmOpen(false)}
        onConfirm={handleConfirmComplete}
        isLoading={isPending}
      />
    </div>
  )
}

export default StudentForm
