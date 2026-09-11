import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { useParams } from 'react-router-dom'
import ActionBar from '@/components/shared/ActionBar'
import { Table, TableWrapper } from '@/components/shared'
import { Button } from '@/components/ui'
import { Capability } from '@/features/auth/capabilities'
import { useCan } from '@/features/auth/hooks'
import {
  approveClassTeacherStudents,
  getClassTeacherAssessmentDetail,
} from '@/features/classes/services'
import type {
  ClassAssessmentDetailStudent,
  ClassAssessmentStudentStatus,
} from '@/features/classes/assessment/types'
import { getApiErrorMessage, mergeClasses } from '@/utils'
import BulkApproveModal from './components/BulkApproveModal'

type StatusFilter = 'all' | ClassAssessmentStudentStatus

const statusLabel = (status: ClassAssessmentStudentStatus) => {
  if (status === 'awaiting_approval') return 'Awaiting approval'
  if (status === 'approved') return 'Approved'
  return 'Pending'
}

const statusChipClass = (status: ClassAssessmentStudentStatus) =>
  mergeClasses(
    'inline-flex rounded-md px-2 py-0.5 text-xs font-medium',
    status === 'approved' && 'bg-emerald-50 text-emerald-800',
    status === 'awaiting_approval' && 'bg-blue-50 text-blue-800',
    status === 'pending' && 'bg-amber-50 text-amber-800',
  )

const formatScore = (value: number | null | undefined) => {
  if (value === null || value === undefined) return '—'
  return Number.isInteger(value) ? String(value) : value.toFixed(2)
}

const formatOrdinal = (value: number) => {
  const mod100 = value % 100
  if (mod100 >= 11 && mod100 <= 13) return `${value}th`
  const mod10 = value % 10
  if (mod10 === 1) return `${value}st`
  if (mod10 === 2) return `${value}nd`
  if (mod10 === 3) return `${value}rd`
  return `${value}th`
}

const DETAIL_QUERY_KEY = (id: string) => ['assessments', 'class-teacher', id] as const

const AssessmentDetail = () => {
  const { classTeacherId } = useParams<{ classTeacherId: string }>()
  const queryClient = useQueryClient()
  const canApprove = useCan(Capability.ASSESSMENTS_APPROVE)

  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [selectedStudentId, setSelectedStudentId] = useState<string | null>(null)
  const [remarks, setRemarks] = useState('')
  const [bulkOpen, setBulkOpen] = useState(false)

  const { data, isLoading, isError, error } = useQuery({
    queryKey: DETAIL_QUERY_KEY(classTeacherId ?? ''),
    queryFn: () => getClassTeacherAssessmentDetail(classTeacherId!),
    enabled: Boolean(classTeacherId),
  })

  const filteredStudents = useMemo(() => {
    const students = data?.students ?? []
    if (statusFilter === 'all') return students
    return students.filter((student) => student.status === statusFilter)
  }, [data?.students, statusFilter])

  useEffect(() => {
    if (!filteredStudents.length) {
      setSelectedStudentId(null)
      return
    }
    if (
      selectedStudentId &&
      filteredStudents.some((student) => student.id === selectedStudentId)
    ) {
      return
    }
    const preferred =
      filteredStudents.find((student) => student.status === 'awaiting_approval') ??
      filteredStudents[0]
    setSelectedStudentId(preferred.id)
  }, [filteredStudents, selectedStudentId])

  const selectedStudent: ClassAssessmentDetailStudent | null = useMemo(() => {
    if (!selectedStudentId) return null
    return data?.students.find((student) => student.id === selectedStudentId) ?? null
  }, [data?.students, selectedStudentId])

  useEffect(() => {
    setRemarks(selectedStudent?.class_teacher_remarks ?? '')
  }, [selectedStudent?.id, selectedStudent?.class_teacher_remarks])

  const { mutate: approveStudents, isPending: isApproving } = useMutation({
    mutationFn: (payload: { student_ids: string[]; remarks?: string }) =>
      approveClassTeacherStudents(classTeacherId!, payload),
    onSuccess: (payload) => {
      toast.success('Students approved')
      queryClient.setQueryData(DETAIL_QUERY_KEY(classTeacherId!), payload)
      void queryClient.invalidateQueries({ queryKey: ['assessments', 'my-classes'] })
      setBulkOpen(false)
    },
    onError: (err) => toast.error(getApiErrorMessage(err, 'Unable to approve students')),
  })

  const awaitingIds =
    data?.students
      .filter((student) => student.status === 'awaiting_approval')
      .map((student) => student.id) ?? []

  const pillTabs: Array<{ key: StatusFilter; label: string; count: number }> = [
    { key: 'all', label: 'All', count: data?.students_count ?? 0 },
    { key: 'pending', label: 'Pending', count: data?.pending_count ?? 0 },
    {
      key: 'awaiting_approval',
      label: 'Awaiting approval',
      count: data?.awaiting_approval_count ?? 0,
    },
    { key: 'approved', label: 'Approved', count: data?.approved_count ?? 0 },
  ]

  const weights = data?.weights
  const canApproveSelected = selectedStudent?.status === 'awaiting_approval' && canApprove

  return (
    <div className="space-y-6">
      <ActionBar title="Assessment details" back />

      {isLoading ? (
        <p className="text-sm text-slate-500">Loading assessment details…</p>
      ) : isError || !data ? (
        <p className="text-sm text-red-600" role="alert">
          {getApiErrorMessage(error, 'Unable to load assessment details.')}
        </p>
      ) : (
        <div className="grid grid-cols-1 gap-4 xl:grid-cols-12 min-h-[70vh]">
          <aside className="xl:col-span-4 bg-white p-4 custom-shadow-md flex flex-col gap-4">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h2 className="text-lg font-medium text-slate-900">{data.display_name}</h2>
                <p className="text-sm text-slate-500 mt-0.5">
                  {data.students_count} student{data.students_count === 1 ? '' : 's'}
                </p>
              </div>
              {canApprove ? (
                <Button
                  type="button"
                  variant="outline"
                  className="max-w-fit py-2 text-sm"
                  disabled={awaitingIds.length === 0}
                  onClick={() => setBulkOpen(true)}
                >
                  Approve all awaiting
                </Button>
              ) : null}
            </div>

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
                        ? 'bg-slate-900 text-white'
                        : 'bg-slate-100 text-slate-600 hover:bg-slate-200',
                    )}
                  >
                    {tab.label} {tab.count}
                  </button>
                )
              })}
            </div>

            <div className="border-t border-slate-200" />

            <ul className="flex-1 space-y-2 overflow-y-auto min-h-0 pr-1">
              {filteredStudents.length === 0 ? (
                <li className="text-sm text-slate-500 py-4">No students in this filter.</li>
              ) : (
                filteredStudents.map((student) => {
                  const selected = student.id === selectedStudentId
                  return (
                    <li key={student.id}>
                      <button
                        type="button"
                        onClick={() => setSelectedStudentId(student.id)}
                        className={mergeClasses(
                          'w-full rounded-lg border px-3 py-3 text-left transition-colors cursor-pointer',
                          selected
                            ? 'border-slate-900 bg-slate-50'
                            : 'border-slate-200 bg-white hover:border-slate-300',
                        )}
                      >
                        <div className="flex items-start justify-between gap-2">
                          <div className="min-w-0">
                            <p className="text-sm font-medium text-slate-900 truncate">
                              {student.full_name}
                            </p>
                            <p className="text-xs text-slate-500 mt-0.5">{student.student_id}</p>
                            {student.status === 'pending' ? (
                              <p className="text-xs text-slate-500 mt-1">
                                {student.subjects_published_count}/
                                {student.subjects_required_count} subjects published
                              </p>
                            ) : null}
                          </div>
                          <span className={statusChipClass(student.status)}>
                            {statusLabel(student.status)}
                          </span>
                        </div>
                      </button>
                    </li>
                  )
                })
              )}
            </ul>
          </aside>

          <section className="xl:col-span-8 bg-white p-4 custom-shadow-md flex flex-col gap-4">
            {!selectedStudent ? (
              <p className="text-sm text-slate-500 py-12 text-center">
                Select a student to review their assessment.
              </p>
            ) : (
              <>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div>
                    <h3 className="text-lg font-medium text-slate-900">
                      {selectedStudent.full_name}
                    </h3>
                    <p className="text-sm text-slate-500">{selectedStudent.student_id}</p>
                  </div>
                  <span className={statusChipClass(selectedStudent.status)}>
                    {statusLabel(selectedStudent.status)}
                  </span>
                </div>

                <TableWrapper
                  isEmpty={selectedStudent.subjects.length === 0}
                  emptyState={{
                    title: 'No subjects',
                    description: 'Subjects for this class will appear here.',
                    icon: 'hugeicons:book-open-01',
                  }}
                  variant="form-field"
                >
                  <div className="overflow-x-auto">
                    <Table>
                      <Table.Head>
                        <Table.Row className="border-b-0">
                          <Table.HeaderCell>Subject</Table.HeaderCell>
                          <Table.HeaderCell>
                            Class score{' '}
                            <span className="font-normal text-slate-400">
                              ({weights?.continuous_assessment_weight ?? '—'}%)
                            </span>
                          </Table.HeaderCell>
                          <Table.HeaderCell>
                            Exam{' '}
                            <span className="font-normal text-slate-400">
                              ({weights?.exam_weight ?? '—'}%)
                            </span>
                          </Table.HeaderCell>
                          <Table.HeaderCell>
                            Total <span className="font-normal text-slate-400">(100%)</span>
                          </Table.HeaderCell>
                          {data.uses_grades ? <Table.HeaderCell>Grade</Table.HeaderCell> : null}
                          {data.uses_position ? <Table.HeaderCell>Pos</Table.HeaderCell> : null}
                          <Table.HeaderCell>Remark</Table.HeaderCell>
                          <Table.HeaderCell>Status</Table.HeaderCell>
                        </Table.Row>
                      </Table.Head>
                      <Table.Body>
                        {selectedStudent.subjects.map((subject) => (
                          <Table.Row key={`${selectedStudent.id}-${subject.subject_label}`}>
                            <Table.Cell variant="primary">
                              <div className="space-y-0.5">
                                <p>{subject.subject_label}</p>
                                <p className="text-xs font-normal text-slate-500">
                                  {subject.teacher_name ?? 'No teacher assigned'}
                                </p>
                              </div>
                            </Table.Cell>
                            <Table.Cell>{formatScore(subject.class_score)}</Table.Cell>
                            <Table.Cell>{formatScore(subject.exam)}</Table.Cell>
                            <Table.Cell>{formatScore(subject.total)}</Table.Cell>
                            {data.uses_grades ? (
                              <Table.Cell>{subject.grade ?? '—'}</Table.Cell>
                            ) : null}
                            {data.uses_position ? (
                              <Table.Cell>
                                {subject.position != null
                                  ? formatOrdinal(subject.position)
                                  : '—'}
                              </Table.Cell>
                            ) : null}
                            <Table.Cell>{subject.band_remark ?? '—'}</Table.Cell>
                            <Table.Cell>
                              <span className="text-xs text-slate-600">{subject.status}</span>
                            </Table.Cell>
                          </Table.Row>
                        ))}
                      </Table.Body>
                    </Table>
                  </div>
                </TableWrapper>

                {data.uses_position ? (
                  <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
                    {selectedStudent.overall_position != null &&
                    selectedStudent.overall_cohort_size != null ? (
                      <p>
                        Overall position:{' '}
                        <span className="font-medium text-slate-900">
                          {formatOrdinal(selectedStudent.overall_position)} of{' '}
                          {selectedStudent.overall_cohort_size}
                        </span>
                        {selectedStudent.overall_average != null ? (
                          <span className="text-slate-500">
                            {' '}
                            · Average {formatScore(selectedStudent.overall_average)}%
                          </span>
                        ) : null}
                      </p>
                    ) : (
                      <p className="text-slate-600">
                        Overall position appears once all subjects are published (Awaiting
                        approval or Approved).
                      </p>
                    )}
                  </div>
                ) : null}
                <div className="space-y-2">
                  <label
                    htmlFor="class-teacher-remarks"
                    className="block text-sm font-medium text-slate-700"
                  >
                    Class teacher remarks
                  </label>
                  <textarea
                    id="class-teacher-remarks"
                    rows={4}
                    value={remarks}
                    onChange={(event) => setRemarks(event.target.value)}
                    disabled={!canApproveSelected}
                    className="w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-slate-500 focus:ring-1 focus:ring-slate-400 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-500"
                    placeholder={
                      canApproveSelected
                        ? 'Add remarks for this student before approving'
                        : 'Remarks are available when the student is awaiting approval'
                    }
                  />
                  <div className="flex flex-wrap items-end justify-between gap-3 pt-1">
                    <p className="text-xs text-slate-500">{data.class_teacher_name}</p>
                    {canApproveSelected ? (
                      <Button
                        type="button"
                        className="max-w-fit py-2 text-sm"
                        loading={isApproving}
                        loadingText="Approving"
                        onClick={() =>
                          approveStudents({
                            student_ids: [selectedStudent.id],
                            remarks: remarks.trim(),
                          })
                        }
                      >
                        Approve
                      </Button>
                    ) : null}
                  </div>
                </div>
              </>
            )}
          </section>
        </div>
      )}

      <BulkApproveModal
        open={bulkOpen}
        awaitingCount={awaitingIds.length}
        isSubmitting={isApproving}
        onClose={() => setBulkOpen(false)}
        onConfirm={(sharedRemarks) =>
          approveStudents({
            student_ids: awaitingIds,
            remarks: sharedRemarks,
          })
        }
      />
    </div>
  )
}

export default AssessmentDetail
