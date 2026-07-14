import { useState, type FormEvent } from 'react'
import { Button, FormLabel, Modal } from '@/components/ui'
import type { SubjectForSetup } from '../../types/types'
import { mergeClasses } from '@/utils'

interface AssignSubjectModalProps {
  open: boolean
  targetClassName: string
  subjects: SubjectForSetup[]
  assignedSubjectIds: string[]
  onClose: () => void
  onSubmit: (subjectId: string) => void
}

const AssignSubjectModal = ({
  open,
  targetClassName,
  subjects,
  assignedSubjectIds,
  onClose,
  onSubmit,
}: AssignSubjectModalProps) => {
  const available = subjects.filter(
    (subject) => subject.id && !assignedSubjectIds.includes(subject.id),
  )

  return (
    <Modal open={open} title="Assign subject" onClose={onClose}>
      {open ? (
        <AssignSubjectForm
          key={`${targetClassName}-${available.map((s) => s.id).join(',')}`}
          targetClassName={targetClassName}
          available={available}
          onClose={onClose}
          onSubmit={onSubmit}
        />
      ) : null}
    </Modal>
  )
}

const AssignSubjectForm = ({
  targetClassName,
  available,
  onClose,
  onSubmit,
}: {
  targetClassName: string
  available: SubjectForSetup[]
  onClose: () => void
  onSubmit: (subjectId: string) => void
}) => {
  const [selectedId, setSelectedId] = useState('')
  const [error, setError] = useState('')

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    if (!selectedId) {
      setError('Select a subject')
      return
    }
    onSubmit(selectedId)
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <p className="text-sm text-slate-500">
        Choose a subject from this level to assign to{' '}
        <span className="text-slate-700">{targetClassName}</span>.
      </p>

      <div className="space-y-1.5">
        <FormLabel label="Subject" required />
        {available.length === 0 ? (
          <p className="rounded-lg border border-slate-300 bg-slate-50 px-3 py-3 text-sm text-slate-500">
            All subjects in this level are already assigned to this class.
          </p>
        ) : (
          <div className="max-h-56 space-y-1 overflow-y-auto rounded-lg border border-slate-300 bg-slate-50 p-2">
            {available.map((subject) => {
              const id = subject.id!
              const isSelected = selectedId === id
              return (
                <button
                  key={id}
                  type="button"
                  onClick={() => {
                    setSelectedId(id)
                    if (error) setError('')
                  }}
                  className={mergeClasses(
                    'flex w-full items-center rounded-md px-3 py-2 text-left text-sm transition-colors',
                    isSelected
                      ? 'bg-slate-900 text-white'
                      : 'text-slate-700 hover:bg-slate-200',
                  )}
                >
                  {subject.name}
                </button>
              )
            })}
          </div>
        )}
        {error ? <p className="text-sm text-red-600">{error}</p> : null}
      </div>

      <div className="grid grid-cols-2 gap-3 pt-2">
        <Button type="button" variant="outline" onClick={onClose}>
          Cancel
        </Button>
        <Button type="submit" variant="solid" disabled={available.length === 0}>
          Assign Subject
        </Button>
      </div>
    </form>
  )
}

export default AssignSubjectModal
