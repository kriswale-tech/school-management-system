import toast from 'react-hot-toast'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { ConfirmDialog, TabComponent } from '@/components/shared'
import { AvatarComponent, Modal } from '@/components/ui'
import { getClassAndSubjects } from '@/features/setup/classes-and-subjects/services'
import { getApiErrorMessage } from '@/utils'
import {
  deleteClassTeacherAssignment,
  deleteTeachingAssignment,
} from '../services'
import type { ClassTeacherAssignment, Teacher, TeachingAssignment } from '../types'
import { buildClassOptions, formatClassTeacherAssignmentLabel, formatTeachingAssignmentLabel, getTeacherProfileImage } from '../utils'
import ClassTeacherAssignmentPanel from './ClassTeacherAssignmentPanel'
import TeachingAssignmentPanel from './TeachingAssignmentPanel'

const CLASS_TEACHER_TAB = 'Class Teacher'
const SUBJECTS_TAB = 'Subjects'

type PendingAssignmentDelete =
  | { kind: 'class_teacher'; assignment: ClassTeacherAssignment }
  | { kind: 'teaching'; assignment: TeachingAssignment }

type AssignTeacherModalProps = {
  open: boolean
  teacher: Teacher | null
  onClose: () => void
}

const AssignTeacherModal = ({ open, teacher, onClose }: AssignTeacherModalProps) => {
  const queryClient = useQueryClient()
  const [activeTab, setActiveTab] = useState(CLASS_TEACHER_TAB)
  const [pendingDelete, setPendingDelete] = useState<PendingAssignmentDelete | null>(null)

  const { data: levels = [], isLoading: isLoadingCurriculum } = useQuery({
    queryKey: ['classAndSubjects'],
    queryFn: getClassAndSubjects,
    enabled: open,
  })

  const classOptions = buildClassOptions(levels)

  const { mutate: removeClassTeacherAssignment, isPending: isRemovingClassTeacher } = useMutation({
    mutationFn: deleteClassTeacherAssignment,
    onSuccess: () => {
      toast.success('Class teacher assignment removed')
      void queryClient.invalidateQueries({ queryKey: ['teachers'] })
      setPendingDelete(null)
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, 'Unable to remove class teacher assignment'))
    },
  })

  const { mutate: removeTeachingAssignment, isPending: isRemovingTeaching } = useMutation({
    mutationFn: deleteTeachingAssignment,
    onSuccess: () => {
      toast.success('Subject assignment removed')
      void queryClient.invalidateQueries({ queryKey: ['teachers'] })
      setPendingDelete(null)
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, 'Unable to remove subject assignment'))
    },
  })

  const handleClose = () => {
    setActiveTab(CLASS_TEACHER_TAB)
    setPendingDelete(null)
    onClose()
  }

  const handleConfirmDelete = () => {
    if (!pendingDelete) return

    if (pendingDelete.kind === 'class_teacher') {
      removeClassTeacherAssignment(pendingDelete.assignment.id)
      return
    }

    removeTeachingAssignment(pendingDelete.assignment.id)
  }

  const deleteMessage =
    pendingDelete?.kind === 'class_teacher'
      ? `Remove class teacher role "${formatClassTeacherAssignmentLabel(pendingDelete.assignment)}" from ${teacher?.full_name}?`
      : pendingDelete?.kind === 'teaching'
        ? `Remove subject assignment "${formatTeachingAssignmentLabel(pendingDelete.assignment)}" from ${teacher?.full_name}?`
        : ''

  if (!open || !teacher) return null

  return (
    <>
      <Modal
        open={open}
        title={`Assign — ${teacher.full_name}`}
        onClose={handleClose}
        scrollable
        className="max-w-4xl"
      >
        <div key={teacher.id} className="space-y-6">
          <div className="flex items-center gap-3 rounded-lg border border-slate-200 bg-slate-50 p-4">
            <AvatarComponent
              image={getTeacherProfileImage(teacher)}
              fullName={teacher.full_name}
              size={48}
            />
            <div>
              <p className="font-medium text-slate-900">{teacher.full_name}</p>
              <p className="text-sm text-slate-500">{teacher.phone_number}</p>
            </div>
          </div>

          <TabComponent
            activeTab={activeTab}
            tabs={[
              {
                label: CLASS_TEACHER_TAB,
                onClick: () => setActiveTab(CLASS_TEACHER_TAB),
              },
              {
                label: SUBJECTS_TAB,
                onClick: () => setActiveTab(SUBJECTS_TAB),
              },
            ]}
          />

          {isLoadingCurriculum ? (
            <p className="text-sm text-slate-500">Loading classes and subjects...</p>
          ) : classOptions.length === 0 ? (
            <p className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-3 text-sm text-slate-500">
              No classes are available yet. Complete the Classes and Subjects setup step first.
            </p>
          ) : activeTab === CLASS_TEACHER_TAB ? (
            <ClassTeacherAssignmentPanel
              teacher={teacher}
              classOptions={classOptions}
              onRequestRemove={(assignment) =>
                setPendingDelete({ kind: 'class_teacher', assignment })
              }
            />
          ) : (
            <TeachingAssignmentPanel
              teacher={teacher}
              classOptions={classOptions}
              onRequestRemove={(assignment) =>
                setPendingDelete({ kind: 'teaching', assignment })
              }
            />
          )}
        </div>
      </Modal>

      <ConfirmDialog
        open={Boolean(pendingDelete)}
        title={
          pendingDelete?.kind === 'class_teacher'
            ? 'Remove class teacher role'
            : 'Remove subject assignment'
        }
        message={deleteMessage}
        confirmLabel="Remove"
        onClose={() => setPendingDelete(null)}
        onConfirm={handleConfirmDelete}
        isLoading={isRemovingClassTeacher || isRemovingTeaching}
      />
    </>
  )
}

export default AssignTeacherModal
