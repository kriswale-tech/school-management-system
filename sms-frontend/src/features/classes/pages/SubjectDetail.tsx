import { useState } from 'react'
import { Icon } from '@iconify/react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { useParams } from 'react-router-dom'
import ActionBar from '@/components/shared/ActionBar'
import { ConfirmDialog } from '@/components/shared'
import { Button, DotComponent } from '@/components/ui'
import { getApiErrorMessage } from '@/utils'
import AssignSubjectGroupStudents from '../components/AssignSubjectGroupStudents'
import ClassStudentsTable from '../components/ClassStudentsTable'
import {
  getTeachingAssignmentDetail,
  getTeachingAssignmentStudents,
  unassignSubjectGroupStudents,
} from '../services'
import type { ClassStudent } from '../types'

const SubjectDetail = () => {
  const { assignmentId } = useParams<{ assignmentId: string }>()
  const queryClient = useQueryClient()
  const [assignOpen, setAssignOpen] = useState(false)
  const [pendingUnassign, setPendingUnassign] = useState<ClassStudent | null>(null)

  const {
    data: subject,
    isLoading: isLoadingDetail,
    isError,
    error,
  } = useQuery({
    queryKey: ['classes', 'teaching-assignment', assignmentId],
    queryFn: () => getTeachingAssignmentDetail(assignmentId!),
    enabled: Boolean(assignmentId),
  })

  const { data: studentsData, isLoading: isLoadingStudents } = useQuery({
    queryKey: ['classes', 'teaching-assignment', assignmentId, 'students'],
    queryFn: () => getTeachingAssignmentStudents(assignmentId!),
    enabled: Boolean(assignmentId),
  })

  const { mutate: unassignStudent, isPending: isUnassigning } = useMutation({
    mutationFn: (studentId: string) =>
      unassignSubjectGroupStudents(assignmentId!, [studentId]),
    onSuccess: () => {
      toast.success('Student unassigned from group')
      void queryClient.invalidateQueries({
        queryKey: ['classes', 'teaching-assignment', assignmentId],
      })
      setPendingUnassign(null)
    },
    onError: (err) => {
      toast.error(getApiErrorMessage(err, 'Unable to unassign student'))
    },
  })

  const isGrouped = Boolean(subject?.is_grouped)
  const unassignedCount = subject?.unassigned_students_count ?? 0

  return (
    <div className="space-y-6">
      <ActionBar title="Subject Detail" back={true}>
        {isGrouped && assignmentId ? (
          <Button
            type="button"
            className="py-2 text-sm max-w-fit"
            onClick={() => setAssignOpen(true)}
          >
            <Icon
              icon="hugeicons:plus-sign"
              className="size-4 bg-white text-black rounded-full p-0.5"
            />
            Assign students
          </Button>
        ) : null}
      </ActionBar>

      <div className="bg-white p-4 custom-shadow-md">
        {isLoadingDetail ? (
          <p className="text-sm text-slate-500 py-8">Loading subject details…</p>
        ) : isError || !subject ? (
          <p className="text-sm text-red-600 py-8" role="alert">
            {getApiErrorMessage(error, 'Unable to load subject details.')}
          </p>
        ) : (
          <>
            <h2 className="text-2xl font-medium mb-1">{subject.subject_label}</h2>
            <div className="flex flex-wrap items-center gap-x-0 mb-6">
              <span className="text-sm text-gray-500">{subject.display_class_name}</span>
              <DotComponent />
              <span className="text-sm text-gray-500">
                {subject.students_count}{' '}
                {subject.students_count === 1 ? 'student' : 'students'}
              </span>
            </div>

            {isGrouped && unassignedCount > 0 ? (
              <div
                className="mb-6 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900"
                role="status"
              >
                {unassignedCount}{' '}
                {unassignedCount === 1 ? 'student is' : 'students are'} not in any{' '}
                {subject.subject_name} group yet. Assign unassigned students to this group, or ask
                another group teacher to unassign first if they are already placed.
              </div>
            ) : null}

            <ClassStudentsTable
              students={studentsData?.results ?? []}
              isLoading={isLoadingStudents}
              onUnassignStudent={
                isGrouped
                  ? (student) => {
                      setPendingUnassign(student)
                    }
                  : undefined
              }
            />
          </>
        )}
      </div>

      {assignmentId && subject?.is_grouped && subject.subject_group_name ? (
        <AssignSubjectGroupStudents
          open={assignOpen}
          assignmentId={assignmentId}
          groupName={subject.subject_group_name}
          onClose={() => setAssignOpen(false)}
        />
      ) : null}

      <ConfirmDialog
        open={Boolean(pendingUnassign)}
        title="Unassign student"
        message={
          pendingUnassign
            ? `Remove ${pendingUnassign.full_name} from this subject group? They will become unassigned until another teacher adds them.`
            : ''
        }
        confirmLabel="Unassign"
        onClose={() => setPendingUnassign(null)}
        onConfirm={() => {
          if (!pendingUnassign) return
          unassignStudent(pendingUnassign.id)
        }}
        isLoading={isUnassigning}
      />
    </div>
  )
}

export default SubjectDetail
