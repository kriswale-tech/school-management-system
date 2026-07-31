import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Icon } from '@iconify/react'
import {
  Controller,
  useWatch,
  type Control,
  type FieldErrors,
  type UseFormRegister,
  type UseFormSetValue,
  type UseFieldArrayReturn,
} from 'react-hook-form'
import ChoicePillGroup from '@/components/shared/ChoicePillGroup'
import { Button, FormLabel, InputField, SearchAndSelect, SelectField } from '@/components/ui'
import { getParents } from '@/features/students/services'
import type { Parent } from '@/features/students/types'
import {
  DEFAULT_GUARDIAN,
  GUARDIAN_MODE_OPTIONS,
  RELATIONSHIP_OPTIONS,
} from '../constants'
import type { GuardianMode, StudentFormValues } from '../types'

type GuardianInfoStepProps = {
  register: UseFormRegister<StudentFormValues>
  control: Control<StudentFormValues>
  setValue: UseFormSetValue<StudentFormValues>
  errors: FieldErrors<StudentFormValues>
  guardiansFieldArray: UseFieldArrayReturn<StudentFormValues, 'guardians'>
}

const PARENT_SEARCH_DEBOUNCE_MS = 300
const PARENT_PAGE_SIZE = 20

const GuardianCard = ({
  index,
  canRemove,
  onRemove,
  register,
  control,
  setValue,
  errors,
}: {
  index: number
  canRemove: boolean
  onRemove: () => void
  register: UseFormRegister<StudentFormValues>
  control: Control<StudentFormValues>
  setValue: UseFormSetValue<StudentFormValues>
  errors: FieldErrors<StudentFormValues>
}) => {
  const guardianErrors = errors.guardians?.[index]
  const mode = useWatch({ control, name: `guardians.${index}.mode` }) ?? 'new'
  const parentId = useWatch({ control, name: `guardians.${index}.parent_id` }) ?? ''
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

  const applyMode = (nextMode: GuardianMode) => {
    setValue(`guardians.${index}.mode`, nextMode, { shouldDirty: true, shouldValidate: true })
    setValue(`guardians.${index}.parent_id`, '', { shouldDirty: true })
    setValue(`guardians.${index}.name`, '', { shouldDirty: true })
    setValue(`guardians.${index}.phone_number`, '', { shouldDirty: true })
    setValue(`guardians.${index}.email`, '', { shouldDirty: true })
    setSelectedParent(null)
    setSearchValue('')
    setDebouncedSearch('')
  }

  const applyParent = (selectedId: string) => {
    if (!selectedId) {
      setSelectedParent(null)
      setValue(`guardians.${index}.parent_id`, '', {
        shouldDirty: true,
        shouldValidate: true,
      })
      setValue(`guardians.${index}.name`, '', { shouldDirty: true })
      setValue(`guardians.${index}.phone_number`, '', { shouldDirty: true })
      setValue(`guardians.${index}.email`, '', { shouldDirty: true })
      return
    }

    const parent =
      parents.find((item) => item.id === selectedId) ??
      (selectedParent?.id === selectedId ? selectedParent : null)

    setValue(`guardians.${index}.parent_id`, selectedId, {
      shouldDirty: true,
      shouldValidate: true,
    })
    if (!parent) return

    setSelectedParent(parent)
    setValue(`guardians.${index}.name`, parent.name, { shouldDirty: true })
    setValue(`guardians.${index}.phone_number`, parent.phone_number, { shouldDirty: true })
    setValue(`guardians.${index}.email`, parent.email ?? '', { shouldDirty: true })
  }

  return (
    <div className="space-y-4 rounded-xl border border-slate-200 bg-slate-50 p-4">
      <div className="flex items-center justify-between gap-3">
        <h3 className="text-sm font-medium text-slate-900">Guardian {index + 1}</h3>
        {canRemove ? (
          <button
            type="button"
            onClick={onRemove}
            className="inline-flex items-center gap-1 text-sm text-red-600 hover:text-red-700"
            aria-label={`Remove guardian ${index + 1}`}
          >
            <Icon icon="hugeicons:delete-02" className="size-4" />
            Remove
          </button>
        ) : null}
      </div>

      <div className="space-y-2">
        <FormLabel label="Guardian source" required />
        <ChoicePillGroup
          name={`guardian-mode-${index}`}
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
              error={guardianErrors?.parent_id?.message}
            />
          )}
        </div>
      ) : null}

      <div className="space-y-2">
        <FormLabel label="Guardian Name" required={!isExisting} />
        <InputField
          placeholder="Enter guardian name"
          error={guardianErrors?.name?.message}
          disabled={isExisting}
          {...register(`guardians.${index}.name`)}
        />
      </div>

      <div className="space-y-2">
        <FormLabel label="Primary Phone" required={!isExisting} />
        <InputField
          type="tel"
          placeholder="e.g +233240000000 or 0240000000"
          error={guardianErrors?.phone_number?.message}
          disabled={isExisting}
          {...register(`guardians.${index}.phone_number`)}
        />
      </div>

      <div className="space-y-2">
        <FormLabel label="Email" />
        <InputField
          type="email"
          placeholder="Enter email (optional)"
          error={guardianErrors?.email?.message}
          disabled={isExisting}
          {...register(`guardians.${index}.email`)}
        />
      </div>

      <div className="space-y-2">
        <FormLabel label="Relationship" required />
        <Controller
          name={`guardians.${index}.relationship`}
          control={control}
          render={({ field: relationshipField }) => (
            <SelectField
              options={[...RELATIONSHIP_OPTIONS]}
              value={relationshipField.value}
              onChange={relationshipField.onChange}
              onBlur={relationshipField.onBlur}
              placeholder="Select relationship"
              error={guardianErrors?.relationship?.message}
            />
          )}
        />
      </div>
    </div>
  )
}

const GuardianInfoStep = ({
  register,
  control,
  setValue,
  errors,
  guardiansFieldArray,
}: GuardianInfoStepProps) => {
  const { fields, append, remove } = guardiansFieldArray

  return (
    <div className="space-y-6">
      {fields.map((field, index) => (
        <GuardianCard
          key={field.id}
          index={index}
          canRemove={fields.length > 1}
          onRemove={() => remove(index)}
          register={register}
          control={control}
          setValue={setValue}
          errors={errors}
        />
      ))}

      {typeof errors.guardians?.message === 'string' ? (
        <p role="alert" className="text-sm text-red-600">
          {errors.guardians.message}
        </p>
      ) : null}

      <Button
        type="button"
        variant="outline"
        onClick={() => append({ ...DEFAULT_GUARDIAN })}
        className="w-full"
      >
        <Icon icon="hugeicons:plus-sign" className="size-4" />
        Add another guardian
      </Button>
    </div>
  )
}

export default GuardianInfoStep
