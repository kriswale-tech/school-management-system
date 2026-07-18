import toast from 'react-hot-toast'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Icon } from '@iconify/react'
import { ChoicePillGroup } from '@/components/shared'
import Button from '@/components/ui/Button'
import FormLabel from '@/components/ui/FormLabel'
import InputField from '@/components/ui/InputField'
import { getApiErrorMessage } from '@/utils'
import { createFeeItem, getClasses, getLevels } from '../services'
import {
  buildAppliesToGroupsOptions,
  buildFeeItemPayload,
  ENTIRE_SCHOOL_VALUE,
  STUDENT_TYPE_OPTIONS,
  validateFeeItemForm,
} from '../utils'

const FeesSetupForm = () => {
  const queryClient = useQueryClient()
  const [name, setName] = useState('')
  const [amount, setAmount] = useState('')
  const [appliesToGroups, setAppliesToGroups] = useState(ENTIRE_SCHOOL_VALUE)
  const [appliesToStudents, setAppliesToStudents] = useState('all_students')

  const { data: levels = [] } = useQuery({
    queryKey: ['feeLevels'],
    queryFn: getLevels,
  })

  const { data: classes = [] } = useQuery({
    queryKey: ['feeClasses'],
    queryFn: getClasses,
  })

  const { mutate: addFeeItem, isPending } = useMutation({
    mutationFn: createFeeItem,
    onSuccess: () => {
      toast.success('Fee item added')
      void queryClient.invalidateQueries({ queryKey: ['feeStructures'] })
      setName('')
      setAmount('')
      setAppliesToGroups(ENTIRE_SCHOOL_VALUE)
      setAppliesToStudents('all_students')
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, 'Unable to add fee item'))
    },
  })

  const handleSubmit = () => {
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

    addFeeItem(buildFeeItemPayload({ name, amount, appliesToGroups, appliesToStudents }))
  }

  const appliesToOptions = buildAppliesToGroupsOptions(levels, classes)

  return (
    <div className="form-field-wrapper space-y-6">
      <div className="flex gap-4 items-center justify-between">
        <div className="w-1/2 space-y-2">
          <FormLabel label="Fee Name" required />
          <InputField
            type="text"
            placeholder="Eg. Tuition Fee"
            value={name}
            onChange={(event) => setName(event.target.value)}
            className="rounded-none bg-white py-3"
          />
        </div>
        <div className="w-1/2 space-y-2">
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
            />
          </div>
        </div>
      </div>

      <div className="space-y-4">
        <FormLabel label="Applies to (Groups)" required />
        <ChoicePillGroup
          name="applies-to"
          items={appliesToOptions}
          value={appliesToGroups}
          onChange={setAppliesToGroups}
        />
      </div>

      <div className="space-y-4">
        <FormLabel label="Applies to (Students)" required />
        <ChoicePillGroup
          name="applies-to-students"
          items={STUDENT_TYPE_OPTIONS}
          value={appliesToStudents}
          onChange={setAppliesToStudents}
        />
      </div>

      <div className="flex justify-end pt-2">
        <Button type="button" className="w-fit" onClick={handleSubmit} loading={isPending}>
          <Icon
            icon="hugeicons:plus-sign"
            className="size-4 bg-white text-black rounded-full p-0.5"
          />
          <span>Add Fee Item</span>
        </Button>
      </div>
    </div>
  )
}

export default FeesSetupForm
