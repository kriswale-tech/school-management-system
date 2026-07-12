import { useEffect, useRef, useState, type RefObject } from 'react'
import CheckboxField from '@/components/ui/CheckboxField'
import { Icon } from '@iconify/react'
import Button from '@/components/ui/Button'
import CustomClassModal from './CustomClassModal'
import CustomSubjectModal from './CustomSubjectModal'
import type { ClassForSetup, SubjectForSetup, SubjectScope } from '../../types'

type ClassSubjectCardProps = {
  subject_scope: SubjectScope
  levelClasses?: ClassForSetup[]
} & (
  | { data: ClassForSetup; type: 'class' }
  | { data: SubjectForSetup; type: 'subject' }
)

const getAssociatedClassIds = (subject: SubjectForSetup, classes: ClassForSetup[]) =>
  classes
    .filter((classItem) =>
      classItem.subjects?.some(
        (classSubject) =>
          (subject.id && classSubject.id === subject.id) || classSubject.name === subject.name,
      ),
    )
    .map((classItem) => classItem.id ?? classItem.name)

const ClassSubjectCard = ({
  data,
  type,
  subject_scope = 'level',
  levelClasses = [],
}: ClassSubjectCardProps) => {
  const items = type === 'class' ? (data.streams ?? []) : data.groups
  const showDropdown = type === 'class' ? items.length > 1 : items.length > 0
  const showStreamAndSubjectMiniButtons = subject_scope === 'class' && type === 'class'
  const [isFormOpen, setIsFormOpen] = useState(false)
  const [isEditModalOpen, setIsEditModalOpen] = useState(false)

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
        {showStreamAndSubjectMiniButtons ? (
          <StreamAndSubjectMiniButtons data={data} />
        ) : (
          showDropdown && (
            <DropdownButton
              items={items}
              label={type === 'class' ? 'View Streams' : 'View Groups'}
            />
          )
        )}
      </div>
      {/* Button */}
      <div className="flex items-center gap-2">
        <div className="relative flex-1 overflow-visible">
          <Button className="w-full" variant="ghost" onClick={() => setIsFormOpen((open) => !open)}>
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

        {data.is_editable && (
          <button
            type="button"
            title={type === 'class' ? 'Edit class' : 'Edit subject'}
            aria-label={type === 'class' ? 'Edit class' : 'Edit subject'}
            onClick={() => setIsEditModalOpen(true)}
            className="flex size-10 shrink-0 items-center justify-center rounded-full border border-slate-400 text-slate-600 hover:bg-slate-50 hover:text-slate-900"
          >
            <Icon icon="hugeicons:edit-02" className="size-4" />
          </button>
        )}
      </div>

      {type === 'class' ? (
        <CustomClassModal
          open={isEditModalOpen}
          mode="edit"
          initialName={data.name}
          onClose={() => setIsEditModalOpen(false)}
          onSubmit={() => setIsEditModalOpen(false)}
        />
      ) : (
        <CustomSubjectModal
          open={isEditModalOpen}
          mode="edit"
          subjectScope={subject_scope}
          classes={levelClasses}
          initialName={data.name}
          initialClassIds={getAssociatedClassIds(data, levelClasses)}
          onClose={() => setIsEditModalOpen(false)}
          onSubmit={() => setIsEditModalOpen(false)}
        />
      )}
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

const StreamAndSubjectMiniButtons = ({ data }: { data: ClassForSetup }) => {
  const showStreamButton = data.streams && data.streams.length > 1
  const showSubjectButton = data.subjects && data.subjects.length > 0

  return (
    <div className="flex items-center gap-2">
      {showStreamButton && <StreamCountDropdown streams={data.streams ?? []} />}
      {showSubjectButton && <SubjectCountDropdown subjects={data.subjects ?? []} />}
    </div>
  )
}

const StreamCountDropdown = ({ streams }: { streams: NonNullable<ClassForSetup['streams']> }) => {
  const [isOpen, setIsOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement | null>(null)

  useClickOutside(containerRef, isOpen, () => setIsOpen(false))

  return (
    <div ref={containerRef} className="relative">
      <Button
        type="button"
        variant="ghost"
        title="Class streams"
        className="w-fit rounded-full p-0.5 px-1.5 gap-0.5 text-xs"
        onClick={() => setIsOpen((open) => !open)}
      >
        <Icon icon="ph:tree-structure-light" className="size-4" />
        <span>{streams.length}</span>
      </Button>

      {isOpen && (
        <div className="absolute right-0 top-full z-20 mt-1 min-w-44 bg-white p-2 shadow-lg">
          <ul className="space-y-1">
            {streams.map((stream) => (
              <li
                key={stream.id}
                className="flex items-center justify-between gap-2 px-2 py-1.5 text-sm text-slate-600 hover:bg-slate-50"
              >
                <span className="truncate">{stream.name || stream.full_name}</span>
                <div className="flex shrink-0 items-center gap-0.5">
                  <IconActionButton icon="hugeicons:edit-02" label="Edit stream" />
                  <IconActionButton
                    variant="danger"
                    icon="ic:outline-remove-circle-outline"
                    label="Remove stream from this class"
                  />
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

const SubjectCountDropdown = ({
  subjects,
}: {
  subjects: NonNullable<ClassForSetup['subjects']>
}) => {
  const [isOpen, setIsOpen] = useState(false)
  const containerRef = useRef<HTMLDivElement | null>(null)

  useClickOutside(containerRef, isOpen, () => setIsOpen(false))

  return (
    <div ref={containerRef} className="relative">
      <Button
        type="button"
        variant="ghost"
        title="Class subjects"
        className="w-fit rounded-full p-0.5 px-1.5 gap-0.5 text-xs"
        onClick={() => setIsOpen((open) => !open)}
      >
        <Icon icon="ph:books" className="size-4" />
        <span>{subjects.length}</span>
      </Button>

      {isOpen && (
        <div className="absolute right-0 top-full z-20 mt-1 min-w-44 bg-white p-2 shadow-lg">
          <ul className="space-y-1">
            {subjects.map((subject) => (
              <li
                key={subject.id}
                className="flex items-center justify-between gap-2 px-2 py-1.5 text-sm text-slate-600 hover:bg-slate-50"
              >
                <span className="truncate">{subject.name}</span>
                <IconActionButton
                  variant="danger"
                  icon="ic:outline-remove-circle-outline"
                  label="Remove subject from this class"
                />
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}

const useClickOutside = (
  containerRef: RefObject<HTMLDivElement | null>,
  isOpen: boolean,
  onClose: () => void,
) => {
  useEffect(() => {
    if (!isOpen) return

    const onPointerDown = (event: PointerEvent) => {
      const target = event.target as Node | null
      if (!target) return
      if (containerRef.current && !containerRef.current.contains(target)) {
        onClose()
      }
    }

    window.addEventListener('pointerdown', onPointerDown)
    return () => window.removeEventListener('pointerdown', onPointerDown)
  }, [containerRef, isOpen, onClose])
}

const IconActionButton = ({
  icon,
  label,
  variant = 'default',
}: {
  icon: string
  label: string
  variant?: 'default' | 'danger'
}) => {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      className={
        variant === 'danger'
          ? 'rounded p-1 text-red-600 hover:bg-red-50 hover:text-red-700'
          : 'rounded p-1 text-slate-500 hover:bg-slate-100 hover:text-slate-900'
      }
    >
      <Icon icon={icon} className="size-3.5" />
    </button>
  )
}
