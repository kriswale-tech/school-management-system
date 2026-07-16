import { useEffect, useRef } from 'react'
import { Controller, useForm, useWatch } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Button, FormLabel, InputField, SelectField } from '@/components/ui'
import type { AcademicYearAndTerm, AcademicYearAndTermFormData } from '../types'
import {
  getAcademicYearOptions,
  guessCurrentTerm,
  mapApiToFormData,
  NUMBER_OF_TERMS,
  TERM_OPTIONS,
  TERMS,
} from '../utils'
import TermSchedule from './TermSchedule'

const termSchema = z.object({
  name: z.enum(TERMS),
  start_date: z.string().min(1, 'Start date is required'),
  end_date: z.string().min(1, 'End date is required'),
})

const schema = z
  .object({
    academic_year: z
      .string()
      .min(1, 'Academic year is required')
      .regex(/^\d{4}\/\d{4}$/, 'Academic year must be in YYYY/YYYY format')
      .refine((value) => {
        const [startYear, endYear] = value.split('/')
        return Number(endYear) === Number(startYear) + 1
      }, 'Academic year end must be one year after the start year'),
    current_term: z.enum(TERMS, { message: 'Current term is required' }),
    terms: z.array(termSchema).length(NUMBER_OF_TERMS),
  })
  .superRefine((data, ctx) => {
    data.terms.forEach((term, index) => {
      if (term.start_date && term.end_date && term.start_date > term.end_date) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: 'End date must be on or after start date',
          path: ['terms', index, 'end_date'],
        })
      }
    })

    const [firstTerm, secondTerm, thirdTerm] = data.terms

    if (
      firstTerm?.end_date &&
      secondTerm?.start_date &&
      firstTerm.end_date > secondTerm.start_date
    ) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'Second term must start on or after first term ends',
        path: ['terms', 1, 'start_date'],
      })
    }

    if (
      secondTerm?.end_date &&
      thirdTerm?.start_date &&
      secondTerm.end_date > thirdTerm.start_date
    ) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        message: 'Third term must start on or after second term ends',
        path: ['terms', 2, 'start_date'],
      })
    }

    if (firstTerm?.start_date && thirdTerm?.end_date) {
      const expectedAcademicYear = `${firstTerm.start_date.slice(0, 4)}/${thirdTerm.end_date.slice(0, 4)}`

      if (data.academic_year !== expectedAcademicYear) {
        ctx.addIssue({
          code: z.ZodIssueCode.custom,
          message: `Academic year must be ${expectedAcademicYear} based on term dates`,
          path: ['academic_year'],
        })
      }
    }
  })

interface AcademicYearAndTermFormProps {
  onSubmit: (_data: AcademicYearAndTermFormData) => void
  academicYearAndTerm?: AcademicYearAndTerm
}

const AcademicYearAndTermForm = ({
  onSubmit,
  academicYearAndTerm,
}: AcademicYearAndTermFormProps) => {
  const academicYearOptions = getAcademicYearOptions(5)
  const skipGuessRef = useRef(true)

  const {
    control,
    register,
    handleSubmit,
    reset,
    setValue,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<AcademicYearAndTermFormData>({
    resolver: zodResolver(schema),
    defaultValues: mapApiToFormData(academicYearAndTerm),
  })

  const watchedTerms = useWatch({ control, name: 'terms' })

  useEffect(() => {
    reset(mapApiToFormData(academicYearAndTerm))
    skipGuessRef.current = true
  }, [academicYearAndTerm, reset])

  useEffect(() => {
    if (skipGuessRef.current) {
      skipGuessRef.current = false
      return
    }

    setValue('current_term', guessCurrentTerm(watchedTerms), { shouldValidate: true })
  }, [watchedTerms, setValue])

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      <div className="space-y-2">
        <FormLabel label="Current Academic Year" className="font-normal text-base" required />
        <Controller
          name="academic_year"
          control={control}
          render={({ field }) => (
            <SelectField
              options={academicYearOptions}
              value={field.value}
              onChange={field.onChange}
              onBlur={field.onBlur}
              placeholder="Select an academic year"
              error={errors.academic_year?.message}
            />
          )}
        />
      </div>

      <div className="space-y-2">
        <FormLabel label="Number of Terms" className="font-normal text-base" required />
        <InputField
          placeholder="Enter the number of terms"
          type="number"
          value={NUMBER_OF_TERMS}
          readOnly
        />
      </div>

      <div className="space-y-2">
        <FormLabel label="Term Schedule" className="font-normal text-base" required />
        <div className="space-y-4">
          {TERMS.map((termName, index) => (
            <div key={termName}>
              <input type="hidden" {...register(`terms.${index}.name`)} />
              <TermSchedule
                label={termName}
                startDateRegister={register(`terms.${index}.start_date`)}
                endDateRegister={register(`terms.${index}.end_date`)}
                startDateError={errors.terms?.[index]?.start_date?.message}
                endDateError={errors.terms?.[index]?.end_date?.message}
              />
            </div>
          ))}
        </div>
      </div>

      <div className="space-y-2">
        <FormLabel label="Current Term" className="font-normal text-base" required />
        <Controller
          name="current_term"
          control={control}
          render={({ field }) => (
            <SelectField
              options={TERM_OPTIONS}
              value={field.value}
              onChange={field.onChange}
              onBlur={field.onBlur}
              placeholder="Select current term"
              error={errors.current_term?.message}
            />
          )}
        />
      </div>

      <Button
        type="submit"
        variant="outline"
        loading={isSubmitting}
        loadingText="Saving..."
        disabled={!isDirty}
      >
        Proceed to Next Step
      </Button>
    </form>
  )
}

export default AcademicYearAndTermForm
