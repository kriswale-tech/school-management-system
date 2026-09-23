import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { ConfirmDialog, Table, TableWrapper } from '@/components/shared'
import { Button } from '@/components/ui'
import ActionButton from '@/components/ui/ActionButton'
import AvatarComponent from '@/components/ui/AvatarComponent'
import { getApiErrorMessage, mergeClasses } from '@/utils'
import {
  DEFAULT_ASSESSMENT_WEIGHTS,
  DEFAULT_GRADE_BANDS,
  EXAM_MAX,
  isStudentCaComplete,
  computeStudentResult,
  formatScore,
} from '../assessment/scoring'
import type { CaItem, StudentAssessmentMarks } from '../assessment/types'
import {
  createTeachingAssignmentCaItem,
  deleteTeachingAssignmentCaItem,
  getTeachingAssignmentWorkspace,
  saveTeachingAssignmentMarks,
  unpublishTeachingAssignmentStudents,
  updateTeachingAssignmentCaItem,
} from '../services'
import AddCaItemModal from './AddCaItemModal'

type SubjectAssessmentWorkspaceProps = {
  assignmentId: string
  canRecord: boolean
  isRecording: boolean
  onExitRecording: () => void
  addCaOpen: boolean
  onCloseAddCa: () => void
}

const cloneMarks = (rows: StudentAssessmentMarks[]): StudentAssessmentMarks[] =>
  rows.map((row) => ({
    student_id: row.student_id,
    exam: row.exam,
    ca: { ...row.ca },
  }))

const parseMarkInput = (raw: string): number | null | 'invalid' => {
  const trimmed = raw.trim()
  if (trimmed === '') return null
  const value = Number(trimmed)
  if (!Number.isFinite(value)) return 'invalid'
  return value
}

const workspaceQueryKey = (assignmentId: string) => [
  'classes',
  'teaching-assignment',
  assignmentId,
  'workspace',
]

const SubjectAssessmentWorkspace = ({
  assignmentId,
  canRecord,
  isRecording,
  onExitRecording,
  addCaOpen,
  onCloseAddCa,
}: SubjectAssessmentWorkspaceProps) => {
  const queryClient = useQueryClient()
  const [draftMarks, setDraftMarks] = useState<StudentAssessmentMarks[]>([])
  const [editingItem, setEditingItem] = useState<CaItem | null>(null)
  const [pendingDelete, setPendingDelete] = useState<CaItem | null>(null)
  const [statusFilter, setStatusFilter] = useState<'all' | 'needs_correction'>('all')

  const {
    data: workspace,
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: workspaceQueryKey(assignmentId),
    queryFn: () => getTeachingAssignmentWorkspace(assignmentId),
    enabled: Boolean(assignmentId),
  })

  const caItems = workspace?.ca_items ?? []
  const weights = workspace?.weights ?? DEFAULT_ASSESSMENT_WEIGHTS
  const gradeBands =
    workspace?.grade_bands?.length ? workspace.grade_bands : DEFAULT_GRADE_BANDS
  const students = workspace?.students ?? []
  const needsCorrectionCount = students.filter((student) => student.needs_correction).length
  const visibleStudents = useMemo(() => {
    if (statusFilter === 'needs_correction') {
      return students.filter((student) => student.needs_correction)
    }
    return students
  }, [students, statusFilter])

  const savedMarks: StudentAssessmentMarks[] = useMemo(
    () =>
      students.map((student) => ({
        student_id: student.id,
        ca: { ...student.ca },
        exam: student.exam,
      })),
    [students],
  )

  useEffect(() => {
    if (isRecording) {
      setDraftMarks(cloneMarks(savedMarks))
    }
  }, [isRecording, savedMarks])

  const invalidateWorkspace = () =>
    queryClient.invalidateQueries({ queryKey: workspaceQueryKey(assignmentId) })

  const { mutate: createItem, isPending: isCreating } = useMutation({
    mutationFn: (payload: { name: string; max_marks: number }) =>
      createTeachingAssignmentCaItem(assignmentId, payload),
    onSuccess: () => {
      toast.success('Class assessment added')
      void invalidateWorkspace()
      onCloseAddCa()
    },
    onError: (err) => toast.error(getApiErrorMessage(err, 'Unable to add assessment')),
  })

  const { mutate: updateItem, isPending: isUpdating } = useMutation({
    mutationFn: (payload: { itemId: string; name: string; max_marks: number }) =>
      updateTeachingAssignmentCaItem(assignmentId, payload.itemId, {
        name: payload.name,
        max_marks: payload.max_marks,
      }),
    onSuccess: () => {
      toast.success('Class assessment updated')
      setEditingItem(null)
      void invalidateWorkspace()
    },
    onError: (err) => toast.error(getApiErrorMessage(err, 'Unable to update assessment')),
  })

  const { mutate: removeItem, isPending: isDeleting } = useMutation({
    mutationFn: (itemId: string) => deleteTeachingAssignmentCaItem(assignmentId, itemId),
    onSuccess: () => {
      toast.success('Class assessment removed')
      setPendingDelete(null)
      void invalidateWorkspace()
    },
    onError: (err) => {
      toast.error(getApiErrorMessage(err, 'Unable to remove assessment'))
      setPendingDelete(null)
    },
  })

  const { mutate: saveMarks, isPending: isSaving } = useMutation({
    mutationFn: (payload: {
      students: Array<{
        student_id: string
        ca: Record<string, number>
        exam: number | null
      }>
    }) => saveTeachingAssignmentMarks(assignmentId, payload),
    onSuccess: () => {
      toast.success('Assessment scores saved')
      void invalidateWorkspace()
      onExitRecording()
    },
    onError: (err) => toast.error(getApiErrorMessage(err, 'Unable to save scores')),
  })

  const { mutate: unpublishStudent, isPending: isUnpublishing } = useMutation({
    mutationFn: (studentId: string) =>
      unpublishTeachingAssignmentStudents(assignmentId, [studentId]),
    onSuccess: () => {
      toast.success('Result unpublished — you can edit again')
      void invalidateWorkspace()
      void queryClient.invalidateQueries({ queryKey: ['me', 'teaching'] })
    },
    onError: (err) => toast.error(getApiErrorMessage(err, 'Unable to unpublish')),
  })

  const activeMarks = isRecording ? draftMarks : savedMarks

  const marksByStudent = useMemo(() => {
    const map = new Map<string, StudentAssessmentMarks>()
    for (const row of activeMarks) map.set(row.student_id, row)
    return map
  }, [activeMarks])

  const updateDraftCa = (studentId: string, itemId: string, raw: string) => {
    const parsed = parseMarkInput(raw)
    if (parsed === 'invalid') return
    setDraftMarks((prev) =>
      prev.map((row) =>
        row.student_id === studentId ? { ...row, ca: { ...row.ca, [itemId]: parsed } } : row,
      ),
    )
  }

  const updateDraftExam = (studentId: string, raw: string) => {
    const parsed = parseMarkInput(raw)
    if (parsed === 'invalid') return
    setDraftMarks((prev) =>
      prev.map((row) => (row.student_id === studentId ? { ...row, exam: parsed } : row)),
    )
  }

  const handleCaSubmit = (payload: { name: string; max_marks: number }): string | null => {
    if (editingItem) {
      updateItem({ itemId: editingItem.id, ...payload })
      return null
    }
    createItem(payload)
    return null
  }

  const handleSave = () => {
    if (caItems.length === 0) {
      toast.error('Add at least one class assessment before saving.')
      return
    }
    const editableDraft = draftMarks.filter((row) => {
      const student = students.find((item) => item.id === row.student_id)
      return student && !student.is_published
    })
    if (editableDraft.length === 0) {
      toast.error('All students are published. Unpublish to edit marks.')
      return
    }

    const hasAnyCaMark = (row: (typeof editableDraft)[number]) =>
      caItems.some((item) => {
        const mark = row.ca[item.id]
        return mark !== null && mark !== undefined
      }) || row.exam !== null

    const completeRows: typeof editableDraft = []
    let skippedPartial = 0
    for (const row of editableDraft) {
      if (isStudentCaComplete(row, caItems)) {
        for (const item of caItems) {
          const mark = row.ca[item.id] as number
          if (mark < 0 || mark > item.max_marks) {
            toast.error(`Marks must be between 0 and ${item.max_marks} for ${item.name}.`)
            return
          }
        }
        if (row.exam !== null && row.exam !== undefined) {
          if (row.exam < 0 || row.exam > EXAM_MAX) {
            toast.error(`Exam marks must be between 0 and ${EXAM_MAX}.`)
            return
          }
        }
        completeRows.push(row)
        continue
      }
      if (hasAnyCaMark(row)) {
        skippedPartial += 1
      }
    }

    if (completeRows.length === 0) {
      toast.error(
        skippedPartial > 0
          ? 'Fill every class assessment mark for a student before saving that row. Exam can wait.'
          : 'Fill every class assessment mark for at least one student before saving. Exam can wait.',
      )
      return
    }

    saveMarks(
      {
        students: completeRows.map((row) => {
          const ca: Record<string, number> = {}
          for (const item of caItems) {
            ca[item.id] = row.ca[item.id] as number
          }
          return {
            student_id: row.student_id,
            ca,
            exam: row.exam,
          }
        }),
      },
      {
        onSuccess: () => {
          if (skippedPartial > 0) {
            toast(
              `${skippedPartial} student${skippedPartial === 1 ? '' : 's'} skipped — complete all class assessment marks first.`,
            )
          }
        },
      },
    )
  }

  if (isError) {
    return (
      <p className="text-sm text-red-600 py-6" role="alert">
        {getApiErrorMessage(error, 'Unable to load assessment workspace.')}
      </p>
    )
  }

  const pillTabs: Array<{ key: 'all' | 'needs_correction'; label: string; count: number }> = [
    { key: 'all', label: 'All', count: students.length },
    { key: 'needs_correction', label: 'Needs correction', count: needsCorrectionCount },
  ]

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2 text-xs text-slate-500">
        <p>
          Class score uses {weights.continuous_assessment_weight}% CA · Exam{' '}
          {weights.exam_weight}% (max {EXAM_MAX})
        </p>
        {isRecording ? (
          <p className="text-amber-700">Record mode — enter marks, then save.</p>
        ) : null}
      </div>

      {!isRecording ? (
        <div className="flex flex-wrap gap-1.5" role="tablist" aria-label="Student status filter">
          {pillTabs.map((tab) => {
            const active = statusFilter === tab.key
            return (
              <button
                key={tab.key}
                type="button"
                role="tab"
                aria-selected={active}
                onClick={() => setStatusFilter(tab.key)}
                className={mergeClasses(
                  'rounded-full px-3 py-1 text-xs font-medium transition-colors cursor-pointer',
                  active
                    ? tab.key === 'needs_correction'
                      ? 'bg-orange-700 text-white'
                      : 'bg-slate-900 text-white'
                    : tab.key === 'needs_correction'
                      ? 'bg-orange-50 text-orange-800 hover:bg-orange-100'
                      : 'bg-slate-100 text-slate-600 hover:bg-slate-200',
                )}
              >
                {tab.label} {tab.count}
              </button>
            )
          })}
        </div>
      ) : null}

      <TableWrapper
        isLoading={isLoading}
        isEmpty={!isLoading && visibleStudents.length === 0}
        emptyState={{
          title:
            statusFilter === 'needs_correction'
              ? 'No students need correction'
              : 'No students to assess',
          description:
            statusFilter === 'needs_correction'
              ? 'Students sent back for this subject will appear here.'
              : 'Students on this subject roster will appear in the mark sheet.',
          icon: 'hugeicons:student',
        }}
        skeletonColumns={isRecording ? 5 : 6}
        variant="form-field"
      >
        <div className="overflow-x-auto">
          <Table>
            <Table.Head>
              <Table.Row className="border-b-0">
                <Table.HeaderCell className="sticky left-0 z-10 min-w-[220px] bg-inherit">
                  Student
                </Table.HeaderCell>
                {isRecording ? (
                  <>
                    {caItems.map((item) => (
                      <Table.HeaderCell key={item.id} className="min-w-[120px]">
                        <div className="flex flex-col gap-1">
                          <span className="whitespace-nowrap">
                            {item.name}{' '}
                            <span className="font-normal text-slate-400">/{item.max_marks}</span>
                          </span>
                          {canRecord ? (
                            <div className="flex items-center gap-1">
                              <ActionButton
                                icon="hugeicons:pencil-edit-02"
                                label={`Edit ${item.name}`}
                                onClick={() => setEditingItem(item)}
                              />
                              <ActionButton
                                icon="hugeicons:delete-02"
                                label={`Remove ${item.name}`}
                                onClick={() => setPendingDelete(item)}
                              />
                            </div>
                          ) : null}
                        </div>
                      </Table.HeaderCell>
                    ))}
                    <Table.HeaderCell className="min-w-[100px]">
                      Exam /{EXAM_MAX}
                    </Table.HeaderCell>
                    <Table.HeaderCell className="min-w-[90px]">
                      Total <span className="font-normal text-slate-400">(100%)</span>
                    </Table.HeaderCell>
                  </>
                ) : (
                  <>
                    <Table.HeaderCell>
                      Class score{' '}
                      <span className="font-normal text-slate-400">
                        ({weights.continuous_assessment_weight}%)
                      </span>
                    </Table.HeaderCell>
                    <Table.HeaderCell>
                      Exam{' '}
                      <span className="font-normal text-slate-400">({weights.exam_weight}%)</span>
                    </Table.HeaderCell>
                    <Table.HeaderCell>
                      Total <span className="font-normal text-slate-400">(100%)</span>
                    </Table.HeaderCell>
                    <Table.HeaderCell>Grade</Table.HeaderCell>
                    <Table.HeaderCell>Status</Table.HeaderCell>
                  </>
                )}
              </Table.Row>
            </Table.Head>
            <Table.Body>
              {visibleStudents.map((student) => {
                const marks = marksByStudent.get(student.id) ?? {
                  student_id: student.id,
                  ca: {},
                  exam: null,
                }
                const live = computeStudentResult(marks, caItems, weights, gradeBands)
                const classScore = isRecording ? live.class_score : student.class_score
                const total = isRecording ? live.total : student.total
                const grade = isRecording ? live.grade : student.grade
                const status = isRecording
                  ? student.is_published
                    ? 'Published'
                    : live.status
                  : student.status
                const examDisplay = isRecording ? marks.exam : student.exam
                const locked = student.is_published
                const correctionReason =
                  student.needs_correction && student.correction_reason
                    ? student.correction_reason
                    : null

                return (
                  <Table.Row key={student.id}>
                    <Table.Cell variant="primary" className="sticky left-0 z-10 bg-white">
                      <div className="flex items-center gap-3">
                        <AvatarComponent fullName={student.full_name} size={36} />
                        <div className="space-y-0.5">
                          <p>{student.full_name}</p>
                          <p className="text-xs font-normal text-slate-500">
                            {student.student_id}
                          </p>
                          {correctionReason ? (
                            <p className="text-xs font-normal text-orange-700 line-clamp-2">
                              {correctionReason}
                            </p>
                          ) : null}
                        </div>
                      </div>
                    </Table.Cell>

                    {isRecording ? (
                      <>
                        {caItems.map((item) => {
                          const value = marks.ca[item.id]
                          return (
                            <Table.Cell key={item.id}>
                              {locked ? (
                                <span>{value === null || value === undefined ? '—' : value}</span>
                              ) : (
                                <input
                                  type="number"
                                  min={0}
                                  max={item.max_marks}
                                  step="any"
                                  className="w-20 rounded border border-slate-300 bg-slate-50 px-2 py-1.5 text-sm outline-none focus:border-slate-500 focus:ring-1 focus:ring-slate-400"
                                  value={value === null || value === undefined ? '' : value}
                                  onChange={(event) =>
                                    updateDraftCa(student.id, item.id, event.target.value)
                                  }
                                  aria-label={`${item.name} for ${student.full_name}`}
                                />
                              )}
                            </Table.Cell>
                          )
                        })}
                        <Table.Cell>
                          {locked ? (
                            <span>
                              {marks.exam === null || marks.exam === undefined ? '—' : marks.exam}
                            </span>
                          ) : (
                            <input
                              type="number"
                              min={0}
                              max={EXAM_MAX}
                              step="any"
                              className="w-20 rounded border border-slate-300 bg-slate-50 px-2 py-1.5 text-sm outline-none focus:border-slate-500 focus:ring-1 focus:ring-slate-400"
                              value={
                                marks.exam === null || marks.exam === undefined ? '' : marks.exam
                              }
                              onChange={(event) => updateDraftExam(student.id, event.target.value)}
                              aria-label={`Exam for ${student.full_name}`}
                            />
                          )}
                        </Table.Cell>
                        <Table.Cell>{formatScore(total)}</Table.Cell>
                      </>
                    ) : (
                      <>
                        <Table.Cell>{formatScore(classScore)}</Table.Cell>
                        <Table.Cell>
                          {examDisplay === null || examDisplay === undefined
                            ? '—'
                            : formatScore(examDisplay)}
                        </Table.Cell>
                        <Table.Cell>{formatScore(total)}</Table.Cell>
                        <Table.Cell>{grade ?? '—'}</Table.Cell>
                        <Table.Cell>
                          <div className="flex items-center gap-2">
                            <span
                              className={mergeClasses(
                                'inline-flex rounded-md px-2 py-0.5 text-xs font-medium',
                                student.needs_correction
                                  ? 'bg-orange-50 text-orange-800'
                                  : status === 'Published'
                                    ? 'bg-emerald-50 text-emerald-800'
                                    : status === 'Complete'
                                      ? 'bg-blue-50 text-blue-800'
                                      : 'bg-slate-100 text-slate-600',
                              )}
                            >
                              {student.needs_correction ? 'Needs correction' : status}
                            </span>
                            {canRecord && status === 'Published' ? (
                              <ActionButton
                                icon="hugeicons:undo-02"
                                label={`Unpublish ${student.full_name}`}
                                onClick={() => unpublishStudent(student.id)}
                                className={isUnpublishing ? 'opacity-50' : undefined}
                              />
                            ) : null}
                          </div>
                        </Table.Cell>
                      </>
                    )}
                  </Table.Row>
                )
              })}
            </Table.Body>
          </Table>
        </div>
      </TableWrapper>

      {isRecording && canRecord ? (
        <div className="flex flex-wrap items-center justify-end gap-2 border-t border-slate-100 pt-4">
          <Button
            type="button"
            variant="ghost"
            className="max-w-fit py-2 text-sm"
            onClick={onExitRecording}
            disabled={isSaving}
          >
            Cancel
          </Button>
          <Button
            type="button"
            className="max-w-fit py-2 text-sm"
            onClick={handleSave}
            loading={isSaving}
            loadingText="Saving"
          >
            Save scores
          </Button>
        </div>
      ) : null}

      <AddCaItemModal
        open={addCaOpen || Boolean(editingItem)}
        mode={editingItem ? 'edit' : 'create'}
        initial={editingItem}
        onClose={() => {
          if (isCreating || isUpdating) return
          setEditingItem(null)
          onCloseAddCa()
        }}
        onSubmit={handleCaSubmit}
      />

      <ConfirmDialog
        open={Boolean(pendingDelete)}
        title="Remove class assessment"
        message={
          pendingDelete
            ? `Remove “${pendingDelete.name}”? This is only allowed if no student has marks for it.`
            : ''
        }
        confirmLabel="Remove"
        onClose={() => setPendingDelete(null)}
        onConfirm={() => {
          if (!pendingDelete) return
          removeItem(pendingDelete.id)
        }}
        isLoading={isDeleting}
      />
    </div>
  )
}

export default SubjectAssessmentWorkspace
