import { useState } from 'react'
import { Icon } from '@iconify/react'
import ClassSubjectCard from './ClassSubjectCard'
import CustomClassModal from './CustomClassModal'
import CustomSubjectModal from './CustomSubjectModal'
import Button from '@/components/ui/Button'
import type { LevelForSetup } from '../../types'
import { mergeClasses } from '@/utils'

type AccordionOpenChangeHandler = (_open: boolean) => void

type ClassModalState = { mode: 'add' | 'edit'; initialName?: string } | null
type SubjectModalState = {
  mode: 'add' | 'edit'
  initialName?: string
  initialClassIds?: string[]
} | null

interface LevelClassSubjectAccordionProps {
  level: LevelForSetup
  open?: boolean
  defaultOpen?: boolean
  onOpenChange?: AccordionOpenChangeHandler
}

const LevelClassSubjectAccordion = ({
  level,
  open: openProp,
  defaultOpen = false,
  onOpenChange,
}: LevelClassSubjectAccordionProps) => {
  const [internalOpen, setInternalOpen] = useState(defaultOpen)
  const [isActive, setIsActive] = useState(level.is_active ?? true)
  const [classModal, setClassModal] = useState<ClassModalState>(null)
  const [subjectModal, setSubjectModal] = useState<SubjectModalState>(null)
  const isOpen = openProp ?? internalOpen

  const setOpen = (next: boolean) => {
    if (openProp === undefined) setInternalOpen(next)
    onOpenChange?.(next)
  }

  const toggle = () => {
    if (!isActive) return
    setOpen(!isOpen)
  }

  const handleActiveChange = (active: boolean) => {
    setIsActive(active)
    if (!active) setOpen(false)
  }

  return (
    <div className="form-field-wrapper space-y-6">
      {/* Heading */}
      <div className="flex items-start justify-between">
        {/* Level name and description */}
        <div className={mergeClasses(!isActive && 'opacity-50')}>
          <div className="flex items-center gap-2 mb-2">
            <ToggleButton checked={isActive} onChange={handleActiveChange} />
            <span className="text-lg text-slate-900">{level.name}</span>
            {level.description && <LevelBadge label={level.description} />}
          </div>

          <p className="text-sm text-slate-500">{`${level.name} classes and subjects`}</p>
        </div>

        {/* Icon for toggling showing and hiding the level classes and subjects aka accordion */}
        <div className={mergeClasses(!isActive && 'opacity-50')}>
          <button
            type="button"
            aria-expanded={isOpen}
            disabled={!isActive}
            onClick={toggle}
            className="text-slate-600 hover:text-slate-900 p-1.5 border border-slate-300 rounded-md bg-slate-50 cursor-pointer disabled:cursor-not-allowed disabled:hover:text-slate-600"
          >
            <Icon
              icon="hugeicons:arrow-down-01"
              className={`size-5 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`}
            />
          </button>
        </div>
      </div>

      {/* Classes and subjects container */}
      {isActive && isOpen && (
        <div className="space-y-6">
          <div className="space-y-4">
            <p>Classes Offered</p>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {level.classes.map((classItem) => (
                <ClassSubjectCard
                  key={classItem.id ?? classItem.name}
                  data={classItem}
                  type="class"
                  subject_scope={level.subject_scope}
                />
              ))}
            </div>
            {level.allows_custom_classes && (
              <Button className="w-fit gap-2" onClick={() => setClassModal({ mode: 'add' })}>
                <Icon
                  icon="hugeicons:plus-sign"
                  className="size-4 bg-white text-black rounded-full p-0.5"
                />
                <span>Add Custom Class</span>
              </Button>
            )}
          </div>

          {/* Subjects container */}
          <div className="space-y-4">
            <p>Subjects (GES Standard)</p>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {level.subjects.map((subject) => (
                <ClassSubjectCard
                  key={subject.id ?? subject.name}
                  data={subject}
                  type="subject"
                  subject_scope={level.subject_scope}
                  levelClasses={level.classes}
                />
              ))}
            </div>
            <Button className="w-fit gap-2" onClick={() => setSubjectModal({ mode: 'add' })}>
              <Icon
                icon="hugeicons:plus-sign"
                className="size-4 bg-white text-black rounded-full p-0.5"
              />
              <span>Add Custom Subject</span>
            </Button>
          </div>
        </div>
      )}

      <CustomClassModal
        open={classModal !== null}
        mode={classModal?.mode ?? 'add'}
        initialName={classModal?.initialName}
        onClose={() => setClassModal(null)}
        onSubmit={() => setClassModal(null)}
      />

      <CustomSubjectModal
        open={subjectModal !== null}
        mode={subjectModal?.mode ?? 'add'}
        subjectScope={level.subject_scope}
        classes={level.classes}
        initialName={subjectModal?.initialName}
        initialClassIds={subjectModal?.initialClassIds}
        onClose={() => setSubjectModal(null)}
        onSubmit={() => setSubjectModal(null)}
      />
    </div>
  )
}

export default LevelClassSubjectAccordion

const LevelBadge = ({ label }: { label: string }) => {
  return (
    <div className="rounded-full bg-blue-100 text-blue-800 px-2 py-1 text-xs font-medium">
      <span>{label}</span>
    </div>
  )
}

const ToggleButton = ({
  checked,
  onChange,
}: {
  checked: boolean
  onChange: (_checked: boolean) => void
}) => {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className={mergeClasses(
        'relative h-5 w-10 shrink-0 rounded-full transition-colors duration-200',
        checked ? 'bg-slate-900' : 'bg-slate-300',
      )}
    >
      <span
        className={mergeClasses(
          'absolute top-0.5 left-0.5 size-4 rounded-full bg-white transition-transform duration-200',
          checked && 'translate-x-5',
        )}
      />
    </button>
  )
}
