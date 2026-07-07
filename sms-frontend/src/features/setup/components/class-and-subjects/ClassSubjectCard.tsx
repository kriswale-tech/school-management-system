import { useState } from 'react'
import CheckboxField from '@/components/ui/CheckboxField'
import { Icon } from '@iconify/react'
import Button from '@/components/ui/Button'
import type { ClassForSetup, SubjectForSetup } from '../../types'

type ClassSubjectCardProps =
  | { data: ClassForSetup; type: 'class' }
  | { data: SubjectForSetup; type: 'subject' }

const ClassSubjectCard = ({ data, type }: ClassSubjectCardProps) => {
  const items = type === 'class' ? (data.streams ?? []) : data.groups
  const showDropdown = type === 'class' ? items.length > 1 : items.length > 0
  const [isFormOpen, setIsFormOpen] = useState(false)

  return (
    <div className=" bg-white border border-slate-400 px-4 py-3 space-y-4">
      {/* Checkbox and Name plus options */}
      <div className="flex items-start justify-between gap-2">
        {/* Checkbox */}
        <div className="flex items-baseline gap-2">
          <CheckboxField checked={data.is_active ?? false} />{' '}
          <span className="text-slate-600 text-[15px]">{data.name}</span>
        </div>
        {/*  options */}
        {showDropdown && (
          <DropdownButton items={items} label={type === 'class' ? 'View Streams' : 'View Groups'} />
        )}
      </div>
      {/* Button */}
      <div className="relative overflow-visible">
        <Button
          className="w-full"
          variant="ghost"
          onClick={() => setIsFormOpen((open) => !open)}
        >
          <Icon
            icon="hugeicons:plus-sign"
            className="size-4 bg-white text-black rounded-full p-0.5"
          />
          <span>{type === 'class' ? 'Add Stream' : 'Add Group'}</span>
        </Button>
        {isFormOpen && (
          <ButtonForm type={type} items={items} onClose={() => setIsFormOpen(false)} />
        )}
      </div>
    </div>
  )
}

export default ClassSubjectCard

const DropdownButton = ({
  items,
  label,
}: {
  items: { id?: string; name: string }[]
  label: string
}) => {
  return (
    <button className="flex items-center gap-1 border border-slate-300 px-2 py-1 text-slate-600 hover:text-slate-900 text-xs shrink-0">
      <span>
        {label}
        {items.length > 0 ? ` (${items.length})` : ''}
      </span>{' '}
      <Icon icon="hugeicons:arrow-down-01" className="size-4" />
    </button>
  )
}

const ButtonForm = ({
  type,
  items,
  onClose,
}: {
  type: 'class' | 'subject'
  items: { id?: string; name: string }[]
  onClose: () => void
}) => {
  const [name, setName] = useState('')
  const isClass = type === 'class'
  const addLabel = isClass ? 'Add Stream' : 'Add Group'
  const placeholder = isClass ? 'Enter stream name here' : 'Enter group name here'

  const showList = isClass ? items.length > 1 : items.length > 0

  const handleAdd = () => {
    if (!name.trim()) return
    setName('')
  }

  return (
    <div className="absolute left-0 right-0 top-full z-20 mt-2 bg-white p-4 space-y-4 shadow-lg">
      {showList && (
        <ul className="list-disc list-inside space-y-1 text-sm text-slate-600">
          {items.map((item) => (
            <li key={item.id ?? item.name}>{item.name}</li>
          ))}
        </ul>
      )}

      <input
        type="text"
        value={name}
        onChange={(event) => setName(event.target.value)}
        placeholder={placeholder}
        className="w-full rounded-md border border-slate-400 px-3 py-2 text-sm text-slate-900 placeholder:text-slate-400 outline-none focus:border-slate-600"
      />

      <div className="grid grid-cols-2 gap-2">
        <Button type="button" variant="ghost" onClick={handleAdd}>
          {addLabel}
        </Button>
        <Button type="button" variant="solid" onClick={onClose}>
          Done
        </Button>
      </div>
    </div>
  )
}
