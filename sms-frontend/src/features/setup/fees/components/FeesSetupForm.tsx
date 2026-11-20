import toast from 'react-hot-toast'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { ChoicePillGroup } from '@/components/shared'
import { Button, FormLabel, InputField, Modal } from '@/components/ui'
import { getApiErrorMessage } from '@/utils'
import { getClasses, getLevels } from '../services'
import type { FeeItemFormValues } from '../types'
import {
  buildAppliesToGroupsOptions,
  buildFeeItemPayload,
  ENTIRE_SCHOOL_VALUE,
  STUDENT_TYPE_OPTIONS,
  validateFeeItemForm,
} from '../utils'

type FeesSetupFormProps = {
  open: boolean
  disabled?: boolean
  queryKey?: unknown[]
  onClose: () => void
  onCreate: (payload: FeeItemFormValues) => Promise<unknown>
}

const FeesSetupForm = ({
  open,
  disabled = false,
  queryKey = ['feeStructures'],
  onClose,
  onCreate,
}: FeesSetupFormProps) => {
  const queryClient = useQueryClient()

  const { data: levels = [] } = useQuery({
    queryKey: ['feeLevels'],
    queryFn: getLevels,
    enabled: open,
  })

  const { data: classes = [] } = useQuery({
    queryKey: ['feeClasses'],
    queryFn: getClasses,
    enabled: open,
  })

  const { mutate: addFeeItem, isPending } = useMutation({
    mutationFn: onCreate,
    onSuccess: () => {
      toast.success('Fee item added')
      void queryClient.invalidateQueries({ queryKey })
      onClose()
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, 'Unable to add fee item'))
    },
  })

  if (!open) return null

  return (
    <Modal open={open} title="Add fee item" onClose={onClose} scrollable className="max-w-lg">
      <AddFeeItemForm
        appliesToOptions={buildAppliesToGroupsOptions(levels, classes)}
        disabled={disabled}
        isSaving={isPending}
        onClose={onClose}
        onSubmit={addFeeItem}
      />
    </Modal>
  )
}

type AddFeeItemFormProps = {
  appliesToOptions: ReturnType<typeof buildAppliesToGroupsOptions>
  disabled: boolean
  isSaving: boolean
  onClose: () => void
  onSubmit: (payload: FeeItemFormValues) => void
}

const AddFeeItemForm = ({
  appliesToOptions,
  disabled,
  isSaving,
  onClose,
  onSubmit,
}: AddFeeItemFormProps) => {
  const [name, setName] = useState('')
  const [amount, setAmount] = useState('')
  const [appliesToGroups, setAppliesToGroups] = useState(ENTIRE_SCHOOL_VALUE)
  const [appliesToStudents, setAppliesToStudents] = useState('all_students')

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()

    const validationError = validateFeeItemForm({
      name,
      amount,
      appliesToGroups,
      appliesToStudents,
    })

    if (validationError) {
      toast.error(validationError)
      return
    }

    onSubmit(buildFeeItemPayload({ name, amount, appliesToGroups, appliesToStudents }))
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
      <div className="space-y-2">
        <FormLabel label="Fee Name" required />
        <InputField
          type="text"
          placeholder="Eg. Tuition Fee"
          value={name}
          onChange={(event) => setName(event.target.value)}
          className="rounded-none bg-white py-3"
          disabled={disabled || isSaving}
        />
      </div>

      <div className="space-y-2">
        <FormLabel label="Amount" required />
        <div className="flex border border-slate-300">
          <span className="text text-slate-500 bg-slate-200 px-2 py-1 flex items-center justify-center shrink-0">
            GHS
          </span>
          <InputField
            type="number"
            placeholder="Eg. 5000"
            value={amount}
            onChange={(event) => setAmount(event.target.value)}
            wrapperClassName="min-w-0 flex-1"
            className="rounded-none bg-white py-3 border-none w-full"
            disabled={disabled || isSaving}
          />
        </div>
      </div>

      <div className="space-y-3">
        <FormLabel label="Applies to (Groups)" required />
        <ChoicePillGroup
          name="applies-to"
          items={appliesToOptions}
          value={appliesToGroups}
          onChange={setAppliesToGroups}
        />
      </div>

      <div className="space-y-3">
        <FormLabel label="Applies to (Students)" required />
        <ChoicePillGroup
          name="applies-to-students"
          items={STUDENT_TYPE_OPTIONS}
          value={appliesToStudents}
          onChange={setAppliesToStudents}
        />
      </div>

      <div className="grid grid-cols-2 gap-3 pt-2">
        <Button type="button" variant="outline" onClick={onClose} disabled={isSaving}>
          Cancel
        </Button>
        <Button type="submit" loading={isSaving} disabled={disabled}>
          Add fee item
        </Button>
      </div>
    </form>
  )
}

export default FeesSetupForm
