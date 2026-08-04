import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { zodResolver } from '@hookform/resolvers/zod'
import { Controller, useForm, useWatch } from 'react-hook-form'
import toast from 'react-hot-toast'
import { z } from 'zod'
import ChoicePillGroup from '@/components/shared/ChoicePillGroup'
import {
  Button,
  CheckboxField,
  FormLabel,
  InputField,
  Modal,
  SearchAndSelect,
  SelectField,
} from '@/components/ui'
import { getApiErrorMessage } from '@/utils'
import { addStudentGuardian, getParents } from '@/features/students/services'
import type { GuardianCreatePayload, Parent } from '@/features/students/types'
import {
  GUARDIAN_MODE_OPTIONS,
  RELATIONSHIP_OPTIONS,
} from './student-onboarding/student-form/constants'
import { STUDENT_DETAIL_QUERY_KEY } from '../utils'

const PARENT_SEARCH_DEBOUNCE_MS = 300
const PARENT_PAGE_SIZE = 20

const ghanaPhoneSchema = z
  .string()
  .min(1, { message: 'Primary phone is required' })
  .regex(/^(\+233|0)[0-9]{9}$/, 'Invalid Ghana phone number')

const relationshipSchema = z.enum(
  [
    'father',
    'mother',
    'guardian',
    'other',
    'uncle',
    'aunt',
    'cousin',
    'sibling',
    'grandparent',
  ],
  { message: 'Relationship is required' },
)

const schema = z.discriminatedUnion('mode', [
  z.object({
    mode: z.literal('new'),
    parent_id: z.string(),
    name: z.string().min(1, { message: 'Guardian name is required' }),
    phone_number: ghanaPhoneSchema,
    email: z
      .string()
      .refine((value) => !value || z.string().email().safeParse(value).success, {
        message: 'Invalid email address',
      }),
    relationship: relationshipSchema,
    is_primary: z.boolean(),
    is_emergency_contact: z.boolean(),
  }),
  z.object({
    mode: z.literal('existing'),
    parent_id: z.string().min(1, { message: 'Select an existing parent' }),
    name: z.string(),
    phone_number: z.string(),
    email: z.string(),
    relationship: relationshipSchema,
    is_primary: z.boolean(),
    is_emergency_contact: z.boolean(),
  }),
])

type AddGuardianFormValues = z.infer<typeof schema>

const DEFAULT_VALUES: AddGuardianFormValues = {
  mode: 'new',
  parent_id: '',
  name: '',
  phone_number: '',
  email: '',
  relationship: 'guardian',
  is_primary: false,
  is_emergency_contact: false,
}

type AddGuardianFormProps = {
  open: boolean
  studentId: string
  onClose: () => void
}

type AddGuardianFormContentProps = {
  studentId: string
  onClose: () => void
}

const AddGuardianFormContent = ({ studentId, onClose }: AddGuardianFormContentProps) => {
  const queryClient = useQueryClient()

  const {
    register,
    control,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm<AddGuardianFormValues>({
    resolver: zodResolver(schema),
    defaultValues: DEFAULT_VALUES,
  })

  const mode = useWatch({ control, name: 'mode' }) ?? 'new'
  const parentId = useWatch({ control, name: 'parent_id' }) ?? ''
  const isExisting = mode === 'existing'

  const [searchValue, setSearchValue] = useState('')
  const [debouncedSearch, setDebouncedSearch] = useState('')
  const [selectedParent, setSelectedParent] = useState<Parent | null>(null)

  useEffect(() => {
    const timer = window.setTimeout(() => {
      setDebouncedSearch(searchValue.trim())
    }, PARENT_SEARCH_DEBOUNCE_MS)
    return () => window.clearTimeout(timer)
  }, [searchValue])

  const { data, isLoading, isFetching, isError } = useQuery({
    queryKey: ['parents', 'search', debouncedSearch],
    queryFn: () =>
      getParents({
        search: debouncedSearch || undefined,
        page_size: PARENT_PAGE_SIZE,
      }),
    enabled: isExisting,
  })

  const parents = useMemo(() => data?.results ?? [], [data?.results])

  const parentOptions = useMemo(() => {
    const options = parents.map((parent) => ({
      value: parent.id,
      label: parent.name,
      description: parent.phone_number,
    }))

    if (
      selectedParent &&
      parentId === selectedParent.id &&
      !options.some((option) => option.value === selectedParent.id)
    ) {
      return [
        {
          value: selectedParent.id,
          label: selectedParent.name,
          description: selectedParent.phone_number,
        },
        ...options,
      ]
    }

    return options
  }, [parents, parentId, selectedParent])

  const { mutate: createGuardian, isPending } = useMutation({
    mutationFn: (payload: GuardianCreatePayload) => addStudentGuardian(studentId, payload),
    onSuccess: () => {
      toast.success('Guardian added')
      void queryClient.invalidateQueries({ queryKey: [STUDENT_DETAIL_QUERY_KEY, studentId] })
      onClose()
    },
    onError: (mutationError) => {
      toast.error(getApiErrorMessage(mutationError, 'Unable to add guardian'))
    },
  })

  const applyMode = (nextMode: 'new' | 'existing') => {
    setValue('mode', nextMode, { shouldDirty: true, shouldValidate: true })
    setValue('parent_id', '', { shouldDirty: true })
    setValue('name', '', { shouldDirty: true })
    setValue('phone_number', '', { shouldDirty: true })
    setValue('email', '', { shouldDirty: true })
    setSelectedParent(null)
    setSearchValue('')
    setDebouncedSearch('')
  }

  const applyParent = (selectedId: string) => {
    if (!selectedId) {
      setSelectedParent(null)
      setValue('parent_id', '', { shouldDirty: true, shouldValidate: true })
      setValue('name', '', { shouldDirty: true })
      setValue('phone_number', '', { shouldDirty: true })
      setValue('email', '', { shouldDirty: true })
      return
    }

    const parent =
      parents.find((item) => item.id === selectedId) ??
      (selectedParent?.id === selectedId ? selectedParent : null)

    setValue('parent_id', selectedId, { shouldDirty: true, shouldValidate: true })
    if (!parent) return

    setSelectedParent(parent)
    setValue('name', parent.name, { shouldDirty: true })
    setValue('phone_number', parent.phone_number, { shouldDirty: true })
    setValue('email', parent.email ?? '', { shouldDirty: true })
  }

  const onSubmit = (values: AddGuardianFormValues) => {
    const flags = {
      is_primary: values.is_primary || undefined,
      is_emergency_contact: values.is_emergency_contact || undefined,
    }

    if (values.mode === 'existing') {
      createGuardian({
        parent_id: values.parent_id,
        relationship: values.relationship,
        ...flags,
      })
      return
    }

    createGuardian({
      name: values.name,
      phone_number: values.phone_number,
      email: values.email || undefined,
      relationship: values.relationship,
      ...flags,
    })
  }

  return (
    <Modal open title="Add Guardian" onClose={onClose} scrollable className="max-w-2xl">
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-5">
        <div className="space-y-2">
          <FormLabel label="Guardian source" required />
          <ChoicePillGroup
            name="add-guardian-mode"
            items={GUARDIAN_MODE_OPTIONS}
            value={mode}
            onChange={applyMode}
          />
        </div>

        {isExisting ? (
          <div className="space-y-2">
            <FormLabel label="Select parent" required />
            {isError ? (
              <p role="alert" className="text-sm text-red-600">
                Unable to load parents. Try again.
              </p>
            ) : (
              <SearchAndSelect
                options={parentOptions}
                value={parentId}
                onChange={applyParent}
                searchValue={searchValue}
                onSearchChange={setSearchValue}
                loading={isLoading || isFetching}
                placeholder="Select an existing parent"
                searchPlaceholder="Search by name, phone, or email"
                emptyMessage={
                  debouncedSearch
                    ? 'No parents match your search'
                    : 'No parents found for this school'
                }
                error={errors.parent_id?.message}
              />
            )}
          </div>
        ) : null}

        <div className="space-y-2">
          <FormLabel label="Guardian Name" required={!isExisting} />
          <InputField
            placeholder="Enter guardian name"
            error={errors.name?.message}
            disabled={isExisting}
            {...register('name')}
          />
        </div>

        <div className="space-y-2">
          <FormLabel label="Primary Phone" required={!isExisting} />
          <InputField
            type="tel"
            placeholder="e.g +233240000000 or 0240000000"
            error={errors.phone_number?.message}
            disabled={isExisting}
            {...register('phone_number')}
          />
        </div>

        <div className="space-y-2">
          <FormLabel label="Email" />
          <InputField
            type="email"
            placeholder="Enter email (optional)"
            error={errors.email?.message}
            disabled={isExisting}
            {...register('email')}
          />
        </div>

        <div className="space-y-2">
          <FormLabel label="Relationship" required />
          <Controller
            name="relationship"
            control={control}
            render={({ field }) => (
              <SelectField
                options={[...RELATIONSHIP_OPTIONS]}
                value={field.value}
                onChange={field.onChange}
                onBlur={field.onBlur}
                placeholder="Select relationship"
                error={errors.relationship?.message}
              />
            )}
          />
        </div>

        <div className="space-y-3">
          <CheckboxField {...register('is_primary')}>Make primary guardian</CheckboxField>
          <CheckboxField {...register('is_emergency_contact')}>Emergency contact</CheckboxField>
        </div>

        <div className="grid grid-cols-2 gap-3 pt-2">
          <Button type="button" variant="outline" onClick={onClose} disabled={isPending}>
            Cancel
          </Button>
          <Button type="submit" loading={isPending} loadingText="Adding...">
            Add Guardian
          </Button>
        </div>
      </form>
    </Modal>
  )
}

const AddGuardianForm = ({ open, studentId, onClose }: AddGuardianFormProps) => {
  if (!open) return null

  return <AddGuardianFormContent key={studentId} studentId={studentId} onClose={onClose} />
}

export default AddGuardianForm
