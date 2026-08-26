import toast from 'react-hot-toast'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { Button, Modal, SearchComponent } from '@/components/ui'
import {
  assignSubjectTeacher,
  getClassList,
  getClassSubjects,
} from '@/features/classes/services'
import type { ClassListItem, ClassSubjectRow } from '@/features/classes/types'
import { getApiErrorMessage, mergeClasses } from '@/utils'
import { STAFF_DESK_QUERY_KEY } from '../utils'

type AssignSubjectToTeacherModalProps = {
  open: boolean
  teacherId: string
  teacherName: string
  onClose: () => void
}

const AssignSubjectToTeacherModal = ({
  open,
  teacherId,
  teacherName,
  onClose,
}: AssignSubjectToTeacherModalProps) => {
  if (!open) return null

  return (
    <AssignSubjectToTeacherModalContent
      teacherId={teacherId}
      teacherName={teacherName}
      onClose={onClose}
    />
  )
}

type ContentProps = {
  teacherId: string
  teacherName: string
  onClose: () => void
}

const AssignSubjectToTeacherModalContent = ({
  teacherId,
  teacherName,
  onClose,
}: ContentProps) => {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [selectedClass, setSelectedClass] = useState<ClassListItem | null>(null)
  const [selectedSubject, setSelectedSubject] = useState<ClassSubjectRow | null>(null)

  const { data: classData, isLoading: classesLoading } = useQuery({
    queryKey: ['classes', 'list', { search }],
    queryFn: () => getClassList({ search: search || undefined }),
  })

  const { data: subjectData, isLoading: subjectsLoading } = useQuery({
    queryKey: ['classes', 'subjects', selectedClass?.id],
    queryFn: () => getClassSubjects(selectedClass!.id),
    enabled: Boolean(selectedClass?.id),
  })

  const classes = classData?.results ?? []
  const subjects = subjectData?.results ?? []

  const { mutate: assign, isPending } = useMutation({
    mutationFn: () =>
      assignSubjectTeacher(selectedClass!.id, {
        teacher_id: teacherId,
        class_subject_id: selectedSubject!.class_subject_id,
        subject_group_id: selectedSubject!.subject_group_id,
      }),
    onSuccess: () => {
      toast.success('Subject assigned')
      void queryClient.invalidateQueries({ queryKey: [STAFF_DESK_QUERY_KEY] })
      void queryClient.invalidateQueries({ queryKey: ['classes'] })
      onClose()
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, 'Unable to assign subject'))
    },
  })

  const classEmptyMessage = useMemo(() => {
    if (classesLoading) return 'Loading classes…'
    if (search.trim()) return 'No classes match your search.'
    return 'No classes available for the active term.'
  }, [classesLoading, search])

  const handleSelectClass = (classItem: ClassListItem) => {
    setSelectedClass(classItem)
    setSelectedSubject(null)
  }

  const handleBack = () => {
    setSelectedClass(null)
    setSelectedSubject(null)
  }

  return (
    <Modal open title="Assign Subject" onClose={onClose} scrollable className="max-w-lg">
      <div className="space-y-4">
        <p className="text-sm text-slate-500">
          Assign a subject for{' '}
          <span className="font-medium text-slate-700">{teacherName}</span> to teach. Subjects
          that already have a teacher are marked; assigning will replace them.
        </p>

        {!selectedClass ? (
          <>
            <SearchComponent
              value={search}
              onChange={setSearch}
              debounceMs={200}
              placeholder="Search classes..."
              className="max-w-none"
            />

            <ul className="max-h-80 space-y-2 overflow-y-auto">
              {classes.length === 0 ? (
                <li className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-4 text-sm text-slate-500">
                  {classEmptyMessage}
                </li>
              ) : (
                classes.map((classItem) => (
                  <li key={classItem.id}>
                    <button
                      type="button"
                      onClick={() => handleSelectClass(classItem)}
                      className="flex w-full items-start justify-between gap-3 rounded-lg border border-slate-200 bg-white px-3 py-3 text-left transition-colors hover:border-slate-300 hover:bg-slate-50"
                    >
                      <div className="min-w-0 space-y-1">
                        <p className="font-medium text-slate-900">{classItem.name}</p>
                        <p className="text-sm text-slate-500">{classItem.level_name}</p>
                      </div>
                      <span className="shrink-0 text-xs text-slate-500">
                        {classItem.subjects_count} subjects
                      </span>
                    </button>
                  </li>
                ))
              )}
            </ul>
          </>
        ) : (
          <>
            <div className="flex items-center justify-between gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2">
              <div>
                <p className="text-xs uppercase tracking-wide text-slate-400">Class</p>
                <p className="text-sm font-medium text-slate-900">{selectedClass.name}</p>
              </div>
              <Button type="button" variant="outline" className="w-fit py-1.5 text-sm" onClick={handleBack}>
                Change
              </Button>
            </div>

            <ul className="max-h-80 space-y-2 overflow-y-auto">
              {subjectsLoading ? (
                <li className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-4 text-sm text-slate-500">
                  Loading subjects…
                </li>
              ) : subjects.length === 0 ? (
                <li className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-4 text-sm text-slate-500">
                  No subjects available for this class.
                </li>
              ) : (
                subjects.map((subject) => {
                  const isSelected = selectedSubject?.id === subject.id
                  const hasTeacher = Boolean(subject.teacher)
                  const statusLabel = hasTeacher
                    ? `Assigned: ${subject.teacher?.full_name ?? 'Teacher'}`
                    : 'Unassigned'

                  return (
                    <li key={subject.id}>
                      <button
                        type="button"
                        onClick={() => setSelectedSubject(subject)}
                        className={mergeClasses(
                          'flex w-full items-start justify-between gap-3 rounded-lg border px-3 py-3 text-left transition-colors',
                          isSelected
                            ? 'border-blue-400 bg-blue-50'
                            : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50',
                        )}
                      >
                        <div className="min-w-0 space-y-1">
                          <p className="font-medium text-slate-900">{subject.name}</p>
                          <p className="text-sm text-slate-500">
                            {subject.students_count}{' '}
                            {subject.students_count === 1 ? 'student' : 'students'}
                          </p>
                        </div>
                        <span
                          className={mergeClasses(
                            'shrink-0 text-xs font-medium',
                            hasTeacher ? 'text-amber-700' : 'text-emerald-700',
                          )}
                        >
                          {statusLabel}
                        </span>
                      </button>
                    </li>
                  )
                })
              )}
            </ul>
          </>
        )}

        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="outline" onClick={onClose} disabled={isPending}>
            Cancel
          </Button>
          <Button
            type="button"
            onClick={() => assign()}
            disabled={!selectedClass || !selectedSubject || isPending}
            loading={isPending}
          >
            Assign Subject
          </Button>
        </div>
      </div>
    </Modal>
  )
}

export default AssignSubjectToTeacherModal
