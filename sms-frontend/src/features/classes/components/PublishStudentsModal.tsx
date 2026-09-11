import { useEffect, useMemo, useState } from 'react'
import { Button, CheckboxField, Modal } from '@/components/ui'
import type { AssessmentWorkspaceStudent } from '../assessment/types'

type PublishStudentsModalProps = {
  open: boolean
  students: AssessmentWorkspaceStudent[]
  isPublishing?: boolean
  onClose: () => void
  onPublish: (_studentIds: string[]) => void
}

const PublishStudentsModal = ({
  open,
  students,
  isPublishing = false,
  onClose,
  onPublish,
}: PublishStudentsModalProps) => {
  const completeStudents = useMemo(
    () => students.filter((student) => student.status === 'Complete'),
    [students],
  )
  const completeIds = useMemo(
    () => completeStudents.map((student) => student.id),
    [completeStudents],
  )
  const [selectedIds, setSelectedIds] = useState<string[]>([])

  useEffect(() => {
    if (!open) return
    setSelectedIds(completeIds)
  }, [open, completeIds])

  if (!open) return null

  const allSelected =
    completeIds.length > 0 && completeIds.every((id) => selectedIds.includes(id))

  const toggle = (id: string) => {
    setSelectedIds((current) =>
      current.includes(id) ? current.filter((item) => item !== id) : [...current, id],
    )
  }

  return (
    <Modal open={open} title="Publish results" onClose={onClose} className="max-w-lg">
      <div className="space-y-4">
        <p className="text-sm text-slate-600">
          Choose complete students to publish to the class teacher. Published results are locked
          until unpublished.
        </p>

        {completeStudents.length === 0 ? (
          <p className="text-sm text-slate-500 py-4">
            No complete students to publish. Finish class score and exam for at least one student
            first.
          </p>
        ) : (
          <>
            <CheckboxField
              checked={allSelected}
              onChange={() => setSelectedIds(allSelected ? [] : completeIds)}
            >
              Select all ({completeIds.length})
            </CheckboxField>

            <ul className="max-h-72 space-y-2 overflow-y-auto pr-1">
              {completeStudents.map((student) => {
                const checked = selectedIds.includes(student.id)
                return (
                  <li key={student.id} className="rounded-lg border border-slate-200 bg-white px-3 py-2">
                    <CheckboxField checked={checked} onChange={() => toggle(student.id)}>
                      <span className="flex flex-col gap-0.5 text-left">
                        <span className="text-sm font-medium text-slate-900">
                          {student.full_name}
                        </span>
                        <span className="text-xs font-normal text-slate-500">
                          {student.student_id}
                          {student.total !== null ? ` · Total ${student.total}` : ''}
                        </span>
                      </span>
                    </CheckboxField>
                  </li>
                )
              })}
            </ul>
          </>
        )}

        <div className="flex justify-end gap-2 pt-2">
          <Button
            type="button"
            variant="ghost"
            className="max-w-fit py-2 text-sm"
            onClick={onClose}
            disabled={isPublishing}
          >
            Cancel
          </Button>
          <Button
            type="button"
            className="max-w-fit py-2 text-sm"
            loading={isPublishing}
            loadingText="Publishing"
            disabled={completeStudents.length === 0 || selectedIds.length === 0}
            onClick={() => onPublish(selectedIds)}
          >
            Publish selected ({selectedIds.length})
          </Button>
        </div>
      </div>
    </Modal>
  )
}

export default PublishStudentsModal
