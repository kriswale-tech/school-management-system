import toast from 'react-hot-toast'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState, type FormEvent } from 'react'
import { ChoicePillGroup } from '@/components/shared'
import { Button, FormLabel, InputField, Modal } from '@/components/ui'
import { getApiErrorMessage } from '@/utils'
import { getClasses, getLevels, updateFeeItem } from '../services'
import type { FeeItem } from '../types'
import {
  buildAppliesToGroupsOptions,
  buildFeeItemPayload,
  mapAppliesToGroupsFromApi,
  mapStudentTypeFromApi,
  STUDENT_TYPE_OPTIONS,
  validateFeeItemForm,
} from '../utils'

type EditFeeItemProps = {
  open: boolean
  feeItem: FeeItem | null
  onClose: () => void
}

const EditFeeItem = ({ open, feeItem, onClose }: EditFeeItemProps) => {
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

  const { mutate: saveFeeItem, isPending } = useMutation({
    mutationFn: (payload: Parameters<typeof updateFeeItem>[1]) =>
      updateFeeItem(feeItem!.id, payload),
    onSuccess: () => {
      toast.success('Fee item updated')
      void queryClient.invalidateQueries({ queryKey: ['feeStructures'] })
      onClose()
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, 'Unable to update fee item'))
    },
  })

  if (!open || !feeItem) return null

  return (
    <Modal open={open} title="Edit Fee Item" onClose={onClose}>
      <EditFeeItemForm
        key={feeItem.id}
        feeItem={feeItem}
        appliesToOptions={buildAppliesToGroupsOptions(levels, classes)}
        isSaving={isPending}
        onClose={onClose}
        onSubmit={saveFeeItem}
      />
    </Modal>
  )
}

type EditFeeItemFormProps = {
  feeItem: FeeItem
  appliesToOptions: ReturnType<typeof buildAppliesToGroupsOptions>
  isSaving: boolean
  onClose: () => void
  onSubmit: (payload: Parameters<typeof updateFeeItem>[1]) => void
}

const EditFeeItemForm = ({
  feeItem,
  appliesToOptions,
  isSaving,
  onClose,
  onSubmit,
}: EditFeeItemFormProps) => {
  const [name, setName] = useState(feeItem.name)
  const [amount, setAmount] = useState(feeItem.amount)
  const [appliesToGroups, setAppliesToGroups] = useState(mapAppliesToGroupsFromApi(feeItem))
  const [appliesToStudents, setAppliesToStudents] = useState(mapStudentTypeFromApi(feeItem.student_type))

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
          value={name}
          onChange={(event) => setName(event.target.value)}
          placeholder="Eg. Tuition Fee"
          className="rounded-none bg-white py-3"
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
            value={amount}
            onChange={(event) => setAmount(event.target.value)}
            placeholder="Eg. 5000"
            wrapperClassName="min-w-0 flex-1"
            className="rounded-none bg-white py-3 border-none w-full"
          />
        </div>
      </div>

      <div className="space-y-3">
        <FormLabel label="Applies to (Groups)" required />
        <ChoicePillGroup
          name={`edit-applies-to-${feeItem.id}`}
          items={appliesToOptions}
          value={appliesToGroups}
          onChange={setAppliesToGroups}
        />
      </div>

      <div className="space-y-3">
        <FormLabel label="Applies to (Students)" required />
        <ChoicePillGroup
          name={`edit-applies-to-students-${feeItem.id}`}
          items={STUDENT_TYPE_OPTIONS}
          value={appliesToStudents}
          onChange={setAppliesToStudents}
        />
      </div>

      <div className="grid grid-cols-2 gap-3 pt-2">
        <Button type="button" variant="outline" onClick={onClose} disabled={isSaving}>
          Cancel
        </Button>
        <Button type="submit" loading={isSaving}>
          Save Changes
        </Button>
      </div>
    </form>
  )
}

export default EditFeeItem
