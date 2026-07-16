import FormLabel from '@/components/ui/FormLabel'
import InputField from '@/components/ui/InputField'
import { useState } from 'react'
import ChoicePillGroup from '@/components/shared/ChoicePillGroup'
import Button from '@/components/ui/Button'
import { Icon } from '@iconify/react'

const APPLIES_TO_GROUPS_OPTIONS = [
  { label: 'Entire School', value: 'entire_school' },
  {
    label: 'Level',
    options: [
      { label: 'Primary', value: 'primary' },
      { label: 'Secondary', value: 'secondary' },
      { label: 'Tertiary', value: 'tertiary' },
    ],
  },
  {
    label: 'Class',
    options: [
      { label: 'Class 1', value: 'class_1' },
      { label: 'Class 2', value: 'class_2' },
      { label: 'Class 3', value: 'class_3' },
      { label: 'Class 4', value: 'class_4' },
      { label: 'Class 5', value: 'class_5' },
    ],
  },
]

const APPLIES_TO_STUDENTS_OPTIONS = [
  { label: 'All Students', value: 'all_students' },
  { label: 'New Students Only', value: 'new_students' },
  { label: 'Continuing Students Only', value: 'continuing_students' },
]

const FeesSetupForm = () => {
  const [appliesToGroups, setAppliesToGroups] = useState<string>('entire_school')
  const [appliesToStudents, setAppliesToStudents] = useState<string>('all_students')

  return (
    <div className="form-field-wrapper space-y-6">
      {/* Forms */}
      <div className="flex gap-4 items-center justify-between">
        <div className="w-1/2 space-y-2">
          <FormLabel label="Fee Name" required />
          <InputField
            type="text"
            placeholder="Eg. Tuition Fee"
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
              wrapperClassName="min-w-0 flex-1"
              className="rounded-none bg-white py-3 border-none w-full"
            />
          </div>
        </div>
      </div>

      {/* Applies to (Groups) */}
      <div className="space-y-4">
        <FormLabel label="Applies to (Groups)" required />
        <ChoicePillGroup
          name="applies-to"
          items={APPLIES_TO_GROUPS_OPTIONS}
          value={appliesToGroups}
          onChange={(value) => setAppliesToGroups(value)}
        />
      </div>

      {/* Applies to (Students) */}
      <div className="space-y-4">
        <FormLabel label="Applies to (Students)" required />
        <ChoicePillGroup
          name="applies-to-students"
          items={APPLIES_TO_STUDENTS_OPTIONS}
          value={appliesToStudents}
          onChange={(value) => setAppliesToStudents(value)}
        />
      </div>

      <div className="flex justify-end pt-2">
        <Button type="button" className="w-fit">
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
