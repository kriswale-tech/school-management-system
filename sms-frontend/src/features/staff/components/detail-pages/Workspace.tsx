import { Icon } from '@iconify/react'
import toast from 'react-hot-toast'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { ConfirmDialog } from '@/components/shared'
import { Button } from '@/components/ui'
import {
  deleteClassTeacherAssignment,
  deleteTeachingAssignment,
} from '@/features/setup/teachers/services'
import { getApiErrorMessage } from '@/utils'
import AssignClassToTeacherModal from '../AssignClassToTeacherModal'
import AssignSubjectToTeacherModal from '../AssignSubjectToTeacherModal'
import TeacherAssignmentsWorkspace, {
  TAB_MANAGED,
  TAB_SUBJECT,
  type TeacherAssignmentTab,
} from '../TeacherAssignmentsWorkspace'
import type {
  StaffDeskClassTeacherAssignment,
  StaffDeskDetail,
  StaffDeskTeachingAssignment,
} from '../../types'
import { STAFF_DESK_QUERY_KEY } from '../../utils'

type PendingUnassign =
  | { kind: 'class'; assignment: StaffDeskClassTeacherAssignment }
  | { kind: 'subject'; assignment: StaffDeskTeachingAssignment }

type TeacherWorkspaceProps = {
  staff: StaffDeskDetail
}

const subjectAssignmentLabel = (assignment: StaffDeskTeachingAssignment) => {
  const subjectLabel = assignment.subject_group_name
    ? `${assignment.subject_name} (${assignment.subject_group_name})`
    : assignment.subject_name
  return `${subjectLabel} · ${assignment.display_class_name}`
}

const TeacherWorkspace = ({ staff }: TeacherWorkspaceProps) => {
  const queryClient = useQueryClient()
  const managed = staff.class_teacher_assignments ?? []
  const teaching = staff.teaching_assignments ?? []
  const [activeTab, setActiveTab] = useState<TeacherAssignmentTab>(
    managed.length === 0 && teaching.length > 0 ? TAB_SUBJECT : TAB_MANAGED,
  )
  const [assignClassOpen, setAssignClassOpen] = useState(false)
  const [assignSubjectOpen, setAssignSubjectOpen] = useState(false)
  const [pendingUnassign, setPendingUnassign] = useState<PendingUnassign | null>(null)

  const { mutate: removeClassAssignment, isPending: isRemovingClass } = useMutation({
    mutationFn: deleteClassTeacherAssignment,
    onSuccess: () => {
      toast.success('Class unassigned')
      void queryClient.invalidateQueries({ queryKey: [STAFF_DESK_QUERY_KEY] })
      void queryClient.invalidateQueries({ queryKey: ['classes'] })
      setPendingUnassign(null)
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, 'Unable to unassign class'))
    },
  })

  const { mutate: removeSubjectAssignment, isPending: isRemovingSubject } = useMutation({
    mutationFn: deleteTeachingAssignment,
    onSuccess: () => {
      toast.success('Subject unassigned')
      void queryClient.invalidateQueries({ queryKey: [STAFF_DESK_QUERY_KEY] })
      void queryClient.invalidateQueries({ queryKey: ['classes'] })
      setPendingUnassign(null)
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, 'Unable to unassign subject'))
    },
  })

  const handleConfirmUnassign = () => {
    if (!pendingUnassign) return
    if (pendingUnassign.kind === 'class') {
      removeClassAssignment(pendingUnassign.assignment.id)
      return
    }
    removeSubjectAssignment(pendingUnassign.assignment.id)
  }

  const unassignMessage =
    pendingUnassign?.kind === 'class'
      ? `Unassign ${staff.full_name} as class teacher for "${pendingUnassign.assignment.display_name}"?`
      : pendingUnassign?.kind === 'subject'
        ? `Unassign ${staff.full_name} from "${subjectAssignmentLabel(pendingUnassign.assignment)}"?`
        : ''

  return (
    <>
      <TeacherAssignmentsWorkspace
        managed={managed}
        teaching={teaching}
        activeTab={activeTab}
        onTabChange={setActiveTab}
        classActionLabel="Unassign"
        subjectActionLabel="Unassign"
        onClassAction={(assignment) => setPendingUnassign({ kind: 'class', assignment })}
        onSubjectAction={(assignment) => setPendingUnassign({ kind: 'subject', assignment })}
        footer={
          <div className="flex justify-end pt-2">
            <Button
              type="button"
              className="w-fit py-2 text-sm"
              onClick={() => {
                if (activeTab === TAB_MANAGED) {
                  setAssignClassOpen(true)
                  return
                }
                setAssignSubjectOpen(true)
              }}
            >
              <Icon
                icon="hugeicons:plus-sign"
                className="size-4 bg-white text-black rounded-full p-0.5"
              />
              {activeTab === TAB_MANAGED ? 'Assign Class' : 'Assign Subject'}
            </Button>
          </div>
        }
      />

      <AssignClassToTeacherModal
        open={assignClassOpen}
        teacherId={staff.id}
        teacherName={staff.full_name}
        onClose={() => setAssignClassOpen(false)}
      />

      <AssignSubjectToTeacherModal
        open={assignSubjectOpen}
        teacherId={staff.id}
        teacherName={staff.full_name}
        onClose={() => setAssignSubjectOpen(false)}
      />

      <ConfirmDialog
        open={Boolean(pendingUnassign)}
        title={pendingUnassign?.kind === 'class' ? 'Unassign class' : 'Unassign subject'}
        message={unassignMessage}
        confirmLabel="Unassign"
        onClose={() => setPendingUnassign(null)}
        onConfirm={handleConfirmUnassign}
        isLoading={isRemovingClass || isRemovingSubject}
      />
    </>
  )
}

export default TeacherWorkspace
