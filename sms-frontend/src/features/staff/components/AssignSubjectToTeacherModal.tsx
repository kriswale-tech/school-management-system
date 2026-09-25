import toast from 'react-hot-toast'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { ButtonTabComponent } from '@/components/shared'
import { Button, Modal, SearchComponent } from '@/components/ui'
import {
  assignLevelSubjectTeacher,
  assignSubjectTeacher,
  getClassList,
  getClassSubjects,
  getLevelAssignableSubjects,
  getLevels,
} from '@/features/classes/services'
import type {
  ClassListItem,
  ClassSubjectRow,
  LevelAssignableSubject,
  LevelSubjectTeacherAssignResult,
} from '@/features/classes/types'
import { getApiErrorMessage, mergeClasses } from '@/utils'
import { STAFF_DESK_QUERY_KEY } from '../utils'

type AssignMode = 'class' | 'level'

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

const levelSubjectStatus = (subject: LevelAssignableSubject) => {
  if (subject.assigned_classes_count <= 0) return 'Unassigned'
  if (subject.assigned_classes_count >= subject.classes_count) return 'Assigned in all classes'
  return `Assigned in ${subject.assigned_classes_count} of ${subject.classes_count}`
}

const levelAssignMessage = (result: LevelSubjectTeacherAssignResult) => {
  const classLabel = result.assigned_count === 1 ? 'class' : 'classes'
  const assigned = `Assigned ${result.subject_name} in ${result.assigned_count} ${classLabel}`
  if (result.skipped_grouped_classes.length === 0) return assigned
  return `${assigned}. Left grouped classes unchanged: ${result.skipped_grouped_classes.join(', ')}`
}

const AssignSubjectToTeacherModalContent = ({
  teacherId,
  teacherName,
  onClose,
}: ContentProps) => {
  const queryClient = useQueryClient()
  const [mode, setMode] = useState<AssignMode>('class')
  const [search, setSearch] = useState('')
  const [selectedClass, setSelectedClass] = useState<ClassListItem | null>(null)
  const [selectedSubject, setSelectedSubject] = useState<ClassSubjectRow | null>(null)
  const [selectedLevel, setSelectedLevel] = useState<{ id: string; name: string } | null>(null)
  const [selectedLevelSubject, setSelectedLevelSubject] = useState<LevelAssignableSubject | null>(
    null,
  )

  const { data: classData, isLoading: classesLoading } = useQuery({
    queryKey: ['classes', 'list', { search }],
    queryFn: () => getClassList({ search: search || undefined }),
    enabled: mode === 'class' && !selectedClass,
  })

  const { data: subjectData, isLoading: subjectsLoading } = useQuery({
    queryKey: ['classes', 'subjects', selectedClass?.id],
    queryFn: () => getClassSubjects(selectedClass!.id),
    enabled: mode === 'class' && Boolean(selectedClass?.id),
  })

  const { data: levels, isLoading: levelsLoading } = useQuery({
    queryKey: ['academics', 'levels'],
    queryFn: getLevels,
    enabled: mode === 'level' && !selectedLevel,
  })

  const { data: levelSubjectData, isLoading: levelSubjectsLoading } = useQuery({
    queryKey: ['academics', 'levels', selectedLevel?.id, 'assignable-subjects'],
    queryFn: () => getLevelAssignableSubjects(selectedLevel!.id),
    enabled: mode === 'level' && Boolean(selectedLevel?.id),
  })

  const classes = classData?.results ?? []
  const subjects = subjectData?.results ?? []
  const levelSubjects = levelSubjectData?.results ?? []
  const filteredLevels = useMemo(() => {
    const term = search.trim().toLowerCase()
    const rows = levels ?? []
    if (!term) return rows
    return rows.filter((level) => level.name.toLowerCase().includes(term))
  }, [levels, search])

  const invalidateAssignments = () => {
    void queryClient.invalidateQueries({ queryKey: [STAFF_DESK_QUERY_KEY] })
    void queryClient.invalidateQueries({ queryKey: ['classes'] })
  }

  const { mutate: assignByClass, isPending: assigningClass } = useMutation({
    mutationFn: () =>
      assignSubjectTeacher(selectedClass!.id, {
        teacher_id: teacherId,
        class_subject_id: selectedSubject!.class_subject_id,
        subject_group_id: selectedSubject!.subject_group_id,
      }),
    onSuccess: () => {
      toast.success('Subject assigned')
      invalidateAssignments()
      onClose()
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, 'Unable to assign subject'))
    },
  })

  const { mutate: assignByLevel, isPending: assigningLevel } = useMutation({
    mutationFn: () =>
      assignLevelSubjectTeacher(selectedLevel!.id, {
        teacher_id: teacherId,
        subject_id: selectedLevelSubject!.subject_id,
      }),
    onSuccess: (result) => {
      toast.success(levelAssignMessage(result))
      invalidateAssignments()
      onClose()
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, 'Unable to assign subject'))
    },
  })

  const isPending = assigningClass || assigningLevel
  const canAssign =
    mode === 'class'
      ? Boolean(selectedClass && selectedSubject)
      : Boolean(selectedLevel && selectedLevelSubject)

  const classEmptyMessage = useMemo(() => {
    if (classesLoading) return 'Loading classes…'
    if (search.trim()) return 'No classes match your search.'
    return 'No classes available for the active term.'
  }, [classesLoading, search])

  const levelEmptyMessage = useMemo(() => {
    if (levelsLoading) return 'Loading levels…'
    if (search.trim()) return 'No levels match your search.'
    return 'No levels available.'
  }, [levelsLoading, search])

  const switchMode = (next: AssignMode) => {
    setMode(next)
    setSearch('')
    setSelectedClass(null)
    setSelectedSubject(null)
    setSelectedLevel(null)
    setSelectedLevelSubject(null)
  }

  const handleSelectClass = (classItem: ClassListItem) => {
    setSelectedClass(classItem)
    setSelectedSubject(null)
  }

  const handleBackToClasses = () => {
    setSelectedClass(null)
    setSelectedSubject(null)
  }

  const handleSelectLevel = (level: { id: string; name: string }) => {
    setSelectedLevel(level)
    setSelectedLevelSubject(null)
    setSearch('')
  }

  return (
    <Modal open title="Assign Subject" onClose={onClose} scrollable className="max-w-lg">
      <div className="space-y-4">
        <div className="space-y-2 text-sm text-slate-500">
          <p>
            Assign a subject for{' '}
            <span className="font-medium text-slate-700">{teacherName}</span> to teach.
          </p>
          <ul className="list-disc space-y-1 pl-4">
            <li>
              <span className="font-medium text-slate-700">By class</span> picks one class.
            </li>
            <li>
              <span className="font-medium text-slate-700">By level</span> applies the subject to
              every class in that level.
            </li>
            <li>Subjects split into groups stay under By class.</li>
            <li>Assigning replaces any teacher already on those classes.</li>
          </ul>
        </div>

        <ButtonTabComponent
          activeTab={mode === 'class' ? 'By class' : 'By level'}
          tabs={[
            { label: 'By class', onClick: () => switchMode('class') },
            { label: 'By level', onClick: () => switchMode('level') },
          ]}
        />

        {mode === 'class' ? (
          !selectedClass ? (
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
                <Button
                  type="button"
                  variant="outline"
                  className="w-fit py-1.5 text-sm"
                  onClick={handleBackToClasses}
                >
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
          )
        ) : !selectedLevel ? (
          <>
            <SearchComponent
              value={search}
              onChange={setSearch}
              debounceMs={200}
              placeholder="Search levels..."
              className="max-w-none"
            />

            <ul className="max-h-80 space-y-2 overflow-y-auto">
              {filteredLevels.length === 0 ? (
                <li className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-4 text-sm text-slate-500">
                  {levelEmptyMessage}
                </li>
              ) : (
                filteredLevels.map((level) => (
                  <li key={level.id}>
                    <button
                      type="button"
                      onClick={() => handleSelectLevel(level)}
                      className="flex w-full items-start justify-between gap-3 rounded-lg border border-slate-200 bg-white px-3 py-3 text-left transition-colors hover:border-slate-300 hover:bg-slate-50"
                    >
                      <p className="font-medium text-slate-900">{level.name}</p>
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
                <p className="text-xs uppercase tracking-wide text-slate-400">Level</p>
                <p className="text-sm font-medium text-slate-900">{selectedLevel.name}</p>
              </div>
              <Button
                type="button"
                variant="outline"
                className="w-fit py-1.5 text-sm"
                onClick={() => {
                  setSelectedLevel(null)
                  setSelectedLevelSubject(null)
                }}
              >
                Change
              </Button>
            </div>

            <ul className="max-h-80 space-y-2 overflow-y-auto">
              {levelSubjectsLoading ? (
                <li className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-4 text-sm text-slate-500">
                  Loading subjects…
                </li>
              ) : levelSubjects.length === 0 ? (
                <li className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-4 text-sm text-slate-500">
                  No subjects can be assigned across this level. Subjects split into groups are
                  assigned class by class.
                </li>
              ) : (
                levelSubjects.map((subject) => {
                  const isSelected = selectedLevelSubject?.subject_id === subject.subject_id
                  const hasTeacher = subject.assigned_classes_count > 0
                  const classLabel = subject.classes_count === 1 ? 'class' : 'classes'

                  return (
                    <li key={subject.subject_id}>
                      <button
                        type="button"
                        onClick={() => setSelectedLevelSubject(subject)}
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
                            {subject.classes_count} {classLabel}
                          </p>
                        </div>
                        <span
                          className={mergeClasses(
                            'shrink-0 text-xs font-medium',
                            hasTeacher ? 'text-amber-700' : 'text-emerald-700',
                          )}
                        >
                          {levelSubjectStatus(subject)}
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
            onClick={() => (mode === 'class' ? assignByClass() : assignByLevel())}
            disabled={!canAssign || isPending}
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
