import { Icon } from '@iconify/react'
import toast from 'react-hot-toast'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { ButtonTabComponent, ConfirmDialog } from '@/components/shared'
import { Button } from '@/components/ui'
import {
  deleteClassTeacherAssignment,
  deleteTeachingAssignment,
} from '@/features/setup/teachers/services'
import { getApiErrorMessage } from '@/utils'
import AssignClassToTeacherModal from '../AssignClassToTeacherModal'
import AssignSubjectToTeacherModal from '../AssignSubjectToTeacherModal'
import type {
  StaffDeskClassTeacherAssignment,
  StaffDeskDetail,
  StaffDeskTeachingAssignment,
} from '../../types'
import { STAFF_DESK_QUERY_KEY } from '../../utils'

const TAB_MANAGED = 'Managed Classes'
const TAB_SUBJECT = 'Subject Teaching'

type PendingUnassign =
  | { kind: 'class'; assignment: StaffDeskClassTeacherAssignment }
  | { kind: 'subject'; assignment: StaffDeskTeachingAssignment }

type TeacherWorkspaceProps = {
  staff: StaffDeskDetail
}

const sumStudents = (counts: number[]) => counts.reduce((total, count) => total + count, 0)

const subjectAssignmentLabel = (assignment: StaffDeskTeachingAssignment) => {
  const subjectLabel = assignment.subject_group_name
    ? `${assignment.subject_name} (${assignment.subject_group_name})`
    : assignment.subject_name
  return `${subjectLabel} · ${assignment.display_class_name}`
}

const ManagedClassCard = ({
  assignment,
  onUnassign,
}: {
  assignment: StaffDeskClassTeacherAssignment
  onUnassign: () => void
}) => (
  <div className="flex flex-col justify-between rounded-lg border border-slate-200 bg-white p-4 custom-shadow-sm">
    <div className="flex items-start justify-between gap-3 mb-4">
      <p className="text-base font-medium text-slate-900">{assignment.display_name}</p>
      <div className="flex items-center gap-1 text-slate-600 shrink-0">
        <Icon icon="hugeicons:user-group" className="size-4" aria-hidden />
        <span className="text-sm">{assignment.students_count}</span>
      </div>
    </div>
    <Button type="button" className="py-2 text-sm" onClick={onUnassign}>
      Unassign
    </Button>
  </div>
)

const SubjectTeachingCard = ({
  assignment,
  onUnassign,
}: {
  assignment: StaffDeskTeachingAssignment
  onUnassign: () => void
}) => {
  const subjectLabel = assignment.subject_group_name
    ? `${assignment.subject_name} (${assignment.subject_group_name})`
    : assignment.subject_name

  return (
    <div className="flex flex-col justify-between rounded-lg border border-slate-200 bg-white p-4 custom-shadow-sm">
      <div className="space-y-1 mb-4">
        <div className="flex items-start justify-between gap-3">
          <p className="text-base font-medium text-slate-900">{subjectLabel}</p>
          <div className="flex items-center gap-1 text-slate-600 shrink-0">
            <Icon icon="hugeicons:user-group" className="size-4" aria-hidden />
            <span className="text-sm">{assignment.students_count}</span>
          </div>
        </div>
        <p className="text-sm text-slate-500">{assignment.display_class_name}</p>
      </div>
      <Button type="button" className="py-2 text-sm" onClick={onUnassign}>
        Unassign
      </Button>
    </div>
  )
}

const TeacherWorkspace = ({ staff }: TeacherWorkspaceProps) => {
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState(TAB_MANAGED)
  const [assignClassOpen, setAssignClassOpen] = useState(false)
  const [assignSubjectOpen, setAssignSubjectOpen] = useState(false)
  const [pendingUnassign, setPendingUnassign] = useState<PendingUnassign | null>(null)

  const managed = staff.class_teacher_assignments ?? []
  const teaching = staff.teaching_assignments ?? []

  const stats = useMemo(() => {
    if (activeTab === TAB_MANAGED) {
      return {
        primaryLabel: `${managed.length} ${managed.length === 1 ? 'Class' : 'Classes'}`,
        primaryIcon: 'hugeicons:notebook-01',
        students: sumStudents(managed.map((item) => item.students_count)),
      }
    }

    return {
      primaryLabel: `${teaching.length} ${teaching.length === 1 ? 'Subject' : 'Subjects'}`,
      primaryIcon: 'hugeicons:book-open-01',
      students: sumStudents(teaching.map((item) => item.students_count)),
    }
  }, [activeTab, managed, teaching])

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
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <ButtonTabComponent
          activeTab={activeTab}
          tabs={[
            {
              label: TAB_MANAGED,
              onClick: () => setActiveTab(TAB_MANAGED),
            },
            {
              label: TAB_SUBJECT,
              onClick: () => setActiveTab(TAB_SUBJECT),
            },
          ]}
        />
        <div className="flex items-center gap-4 text-sm text-slate-600">
          <div className="flex items-center gap-1.5">
            <Icon icon={stats.primaryIcon} className="size-4" aria-hidden />
            <span>{stats.primaryLabel}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Icon icon="hugeicons:user-group" className="size-4" aria-hidden />
            <span>
              {stats.students} {stats.students === 1 ? 'Student' : 'Students'}
            </span>
          </div>
        </div>
      </div>

      {activeTab === TAB_MANAGED ? (
        managed.length === 0 ? (
          <p className="text-sm text-slate-500 py-6">No managed classes for the active term.</p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {managed.map((assignment) => (
              <ManagedClassCard
                key={assignment.id}
                assignment={assignment}
                onUnassign={() => setPendingUnassign({ kind: 'class', assignment })}
              />
            ))}
          </div>
        )
      ) : teaching.length === 0 ? (
        <p className="text-sm text-slate-500 py-6">No subject teaching for the active term.</p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {teaching.map((assignment) => (
            <SubjectTeachingCard
              key={assignment.id}
              assignment={assignment}
              onUnassign={() => setPendingUnassign({ kind: 'subject', assignment })}
            />
          ))}
        </div>
      )}

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
    </div>
  )
}

export default TeacherWorkspace
