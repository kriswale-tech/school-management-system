import { Icon } from '@iconify/react'
import Button from '@/components/ui/Button'
import type { ClassSubjectForSetup } from '../../../types/types'
import IconActionButton from './IconActionButton'
import { useAnchoredDropdown } from './dropdown-utils'

const SubjectCountDropdown = ({
  subjects,
  onRemove,
  onAddSubject,
}: {
  subjects: ClassSubjectForSetup[]
  onRemove: (subjectId: string, subjectName: string) => void
  onAddSubject: () => void
}) => {
  const { isOpen, panelStyle, containerRef, toggleOpen, close } = useAnchoredDropdown()

  return (
    <div ref={containerRef} className="relative">
      <Button
        type="button"
        variant="ghost"
        title="Class subjects"
        className="w-fit rounded-full p-0.5 px-1.5 gap-0.5 text-xs"
        onClick={toggleOpen}
      >
        <Icon icon="ph:books" className="size-4" />
        <span>{subjects.length}</span>
      </Button>

      {isOpen && (
        <div className="bg-white p-2 shadow-lg" style={panelStyle}>
          <ul className="max-h-52 space-y-1 overflow-y-auto">
            {subjects.length === 0 ? (
              <li className="px-2 py-1.5 text-sm text-slate-400">No subjects assigned</li>
            ) : (
              subjects.map((subject) => (
                <li
                  key={subject.id}
                  className="flex items-center justify-between gap-2 px-2 py-1.5 text-sm text-slate-600 hover:bg-slate-50"
                >
                  <span className="min-w-0 flex-1 truncate" title={subject.name}>
                    {subject.name}
                  </span>
                  <IconActionButton
                    variant="danger"
                    icon="ic:outline-remove-circle-outline"
                    label="Remove subject from this class"
                    onClick={() => {
                      onRemove(subject.id, subject.name)
                      close()
                    }}
                  />
                </li>
              ))
            )}
          </ul>

          <button
            type="button"
            onClick={() => {
              close()
              onAddSubject()
            }}
            className="mt-2 flex w-full items-center justify-center gap-1 border border-slate-300 px-2 py-1.5 text-xs text-slate-700 hover:bg-slate-50"
          >
            <Icon icon="hugeicons:plus-sign" className="size-3.5" />
            <span>Add subject</span>
          </button>
        </div>
      )}
    </div>
  )
}

export default SubjectCountDropdown
