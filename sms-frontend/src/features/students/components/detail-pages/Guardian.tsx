import { useState } from 'react'
import { Icon } from '@iconify/react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { ConfirmDialog } from '@/components/shared'
import Button from '@/components/ui/Button'
import { getApiErrorMessage } from '@/utils'
import { deleteStudentGuardian } from '../../services'
import type { StudentGuardian } from '../../types'
import { STUDENT_DETAIL_QUERY_KEY } from '../../utils'
import { RELATIONSHIP_OPTIONS } from '../student-onboarding/student-form/constants'
import AddGuardianForm from '../AddGuardianForm'
import EditGuardianForm from '../EditGuardianForm'

type GuardianProps = {
  studentId: string
  guardians: StudentGuardian[]
}

const getRelationshipLabel = (value: StudentGuardian['relationship']) =>
  RELATIONSHIP_OPTIONS.find((option) => option.value === value)?.label ?? value

const Guardian = ({ studentId, guardians }: GuardianProps) => {
  const queryClient = useQueryClient()
  const [addOpen, setAddOpen] = useState(false)
  const [editingGuardian, setEditingGuardian] = useState<StudentGuardian | null>(null)
  const [removingGuardian, setRemovingGuardian] = useState<StudentGuardian | null>(null)

  const { mutate: removeGuardian, isPending: isRemoving } = useMutation({
    mutationFn: (linkId: string) => deleteStudentGuardian(studentId, linkId),
    onSuccess: () => {
      toast.success('Guardian removed')
      void queryClient.invalidateQueries({ queryKey: [STUDENT_DETAIL_QUERY_KEY, studentId] })
      setRemovingGuardian(null)
    },
    onError: (mutationError) => {
      toast.error(getApiErrorMessage(mutationError, 'Unable to remove guardian'))
    },
  })

  const handleConfirmRemove = () => {
    if (!removingGuardian) return
    removeGuardian(removingGuardian.id)
  }

  const sortedGuardians = [...guardians].sort((a, b) => {
    if (a.is_primary === b.is_primary) return 0
    return a.is_primary ? -1 : 1
  })

  return (
    <>
      <div className="space-y-4">
        <div className="flex items-start justify-between gap-4">
          <p className="text-sm text-slate-500 max-w-xl">
            Manage the student&apos;s guardians and emergency contacts. The primary guardian is
            marked below.
          </p>
          <Button className="w-fit shrink-0" onClick={() => setAddOpen(true)}>
            <Icon icon="hugeicons:plus-sign" className="size-4" />
            Add Guardian
          </Button>
        </div>

        {sortedGuardians.length === 0 ? (
          <p className="text-sm text-slate-500 py-6">No guardians linked to this student.</p>
        ) : (
          <div className="space-y-4">
            {sortedGuardians.map((guardian) => {
              const fields = [
                { label: 'Full Name', value: guardian.name },
                { label: 'Primary Phone', value: guardian.phone_number },
                {
                  label: 'Alternate Phone',
                  value: guardian.phone_number_alt?.trim() || '—',
                },
                { label: 'Email', value: guardian.email || '—' },
                { label: 'Address', value: guardian.address?.trim() || '—' },
                {
                  label: 'Relationship',
                  value: getRelationshipLabel(guardian.relationship),
                },
                {
                  label: 'Emergency Contact',
                  value: guardian.is_emergency_contact ? 'Yes' : 'No',
                },
              ]

              return (
                <div key={guardian.id} className="bg-gray-100 rounded-md px-4 w-full">
                  {guardian.is_primary ? (
                    <div className="pt-4">
                      <span className="text-xs font-medium uppercase tracking-wide text-slate-500">
                        Primary Guardian
                      </span>
                    </div>
                  ) : null}

                  {fields.map((field) => (
                    <div
                      key={field.label}
                      className="flex items-center justify-between py-4 border-b border-slate-300"
                    >
                      <span className="text-slate-500">{field.label}</span>
                      <span className="text-slate-800">{field.value}</span>
                    </div>
                  ))}

                  <div className="flex items-center justify-end gap-3 py-4">
                    <Button className="w-fit" onClick={() => setEditingGuardian(guardian)}>
                      <Icon icon="hugeicons:pencil-edit-02" />
                      Edit
                    </Button>
                    <Button
                      className="w-fit"
                      variant="outline"
                      color="red"
                      onClick={() => setRemovingGuardian(guardian)}
                    >
                      <Icon icon="hugeicons:delete-02" />
                      Remove
                    </Button>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>

      <AddGuardianForm
        open={addOpen}
        studentId={studentId}
        onClose={() => setAddOpen(false)}
      />
      <EditGuardianForm
        open={Boolean(editingGuardian)}
        studentId={studentId}
        guardian={editingGuardian}
        onClose={() => setEditingGuardian(null)}
      />
      <ConfirmDialog
        open={Boolean(removingGuardian)}
        title="Remove guardian"
        message={`Are you sure you want to remove "${removingGuardian?.name}"? This unlinks them from the student but keeps the parent record.`}
        confirmLabel="Remove"
        isLoading={isRemoving}
        onClose={() => setRemovingGuardian(null)}
        onConfirm={handleConfirmRemove}
      />
    </>
  )
}

export default Guardian
