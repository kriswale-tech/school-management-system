import { useEffect, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { useParams, useSearchParams } from 'react-router-dom'
import ActionBar from '@/components/shared/ActionBar'
import { Table, TableWrapper } from '@/components/shared'
import { Button } from '@/components/ui'
import { Capability } from '@/features/auth/capabilities'
import { useCan } from '@/features/auth/hooks'
import {
  getAdminAssessmentDetail,
  releaseAdminAssessmentStudents,
} from '@/features/classes/services'
import type {
  AdminAssessmentDetailStudent,
  AdminAssessmentStudentStatus,
} from '@/features/classes/assessment/types'
import { getApiErrorMessage, mergeClasses } from '@/utils'
import BulkReleaseModal from './components/BulkReleaseModal'

type StatusFilter = 'all' | 'ready_for_you' | 'released'

const statusLabel = (status: AdminAssessmentStudentStatus) => {
  if (status === 'ready_for_you') return 'Ready for you'
  if (status === 'released') return 'Released'
  return 'With class teacher'
}

const statusChipClass = (status: AdminAssessmentStudentStatus) =>
  mergeClasses(
    'inline-flex rounded-md px-2 py-0.5 text-xs font-medium',
    status === 'released' && 'bg-emerald-50 text-emerald-800',
    status === 'ready_for_you' && 'bg-blue-50 text-blue-800',
    status === 'with_class_teacher' && 'bg-amber-50 text-amber-800',
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

const remarksClassName =
  'w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none focus:border-slate-500 focus:ring-1 focus:ring-slate-400 disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-500'

const DETAIL_QUERY_KEY = (id: string, termId: string) =>
  ['assessments', 'admin', 'detail', id, termId] as const

const AdminAssessmentDetail = () => {
  const { streamId } = useParams<{ streamId: string }>()
  const [searchParams] = useSearchParams()
  const termId = searchParams.get('term') ?? undefined
  const queryClient = useQueryClient()
  const canRelease = useCan(Capability.ASSESSMENTS_RELEASE)

  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [selectedStudentId, setSelectedStudentId] = useState<string | null>(null)
  const [headRemarks, setHeadRemarks] = useState('')
  const [bulkOpen, setBulkOpen] = useState(false)

  const { data, isLoading, isError, error } = useQuery({
    queryKey: DETAIL_QUERY_KEY(streamId ?? '', termId ?? ''),
    queryFn: () => getAdminAssessmentDetail(streamId!, termId),
    enabled: Boolean(streamId),
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
    if (selectedStudentId && filteredStudents.some((student) => student.id === selectedStudentId)) {
      return
    }
    const preferred =
      filteredStudents.find((student) => student.status === 'ready_for_you') ?? filteredStudents[0]
    setSelectedStudentId(preferred.id)
  }, [filteredStudents, selectedStudentId])

  const selectedStudent: AdminAssessmentDetailStudent | null = useMemo(() => {
    if (!selectedStudentId) return null
    return data?.students.find((student) => student.id === selectedStudentId) ?? null
  }, [data?.students, selectedStudentId])

  useEffect(() => {
    setHeadRemarks(selectedStudent?.head_teacher_remarks ?? '')
  }, [selectedStudent?.id, selectedStudent?.head_teacher_remarks])

  const { mutate: releaseStudents, isPending: isReleasing } = useMutation({
    mutationFn: (payload: { student_ids: string[]; remarks?: string }) =>
      releaseAdminAssessmentStudents(streamId!, payload, termId),
    onSuccess: (payload) => {
      toast.success('Students released')
      queryClient.setQueryData(DETAIL_QUERY_KEY(streamId ?? '', termId ?? ''), payload)
      void queryClient.invalidateQueries({ queryKey: ['assessments', 'admin', 'classes'] })
      setBulkOpen(false)
    },
    onError: (err) => toast.error(getApiErrorMessage(err, 'Unable to release students')),
  })

  const readyIds =
    data?.students.filter((student) => student.status === 'ready_for_you').map((student) => student.id) ??
    []

  const pillTabs: Array<{ key: StatusFilter; label: string; count: number }> = [
    { key: 'all', label: 'All', count: data?.students_count ?? 0 },
    { key: 'ready_for_you', label: 'Ready for you', count: data?.ready_for_you_count ?? 0 },
    { key: 'released', label: 'Released', count: data?.released_count ?? 0 },
  ]

  const weights = data?.weights
  const canReleaseSelected = selectedStudent?.status === 'ready_for_you' && canRelease
  const canGenerateReport = selectedStudent?.status === 'released'

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
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0 flex-1">
                <h2 className="text-lg font-medium text-slate-900">{data.display_name}</h2>
                <p className="text-sm text-slate-500 mt-0.5">
                  {data.class_teacher_name ?? 'No class teacher'}
                </p>
                <p className="text-sm text-slate-500 mt-0.5">{data.term_label}</p>
                {data.with_class_teacher_count > 0 ? (
                  <p className="text-xs text-slate-400 mt-1">
                    {data.with_class_teacher_count} still with the class teacher — not shown
                  </p>
                ) : null}
              </div>
              {canRelease ? (
                <Button
                  type="button"
                  variant="outline"
                  className="max-w-fit shrink-0 py-2 text-sm"
                  disabled={readyIds.length === 0}
                  onClick={() => setBulkOpen(true)}
                >
                  Release all ready
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

            <ul className="space-y-2 overflow-y-auto">
              {filteredStudents.length === 0 ? (
                <li className="text-sm text-slate-500 py-6 text-center">
                  No students are ready for review yet.
                </li>
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
                                {subject.position != null ? formatOrdinal(subject.position) : '—'}
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
                        Overall position appears once the class teacher has approved the student.
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
                    rows={3}
                    value={selectedStudent.class_teacher_remarks}
                    readOnly
                    disabled
                    className={remarksClassName}
                    placeholder="No class teacher remarks yet"
                  />
                  <div className="flex justify-end">
                    <p className="text-xs text-slate-500">
                      {data.class_teacher_name ?? 'No class teacher'}
                    </p>
                  </div>
                </div>

                <div className="space-y-2">
                  <label
                    htmlFor="head-teacher-remarks"
                    className="block text-sm font-medium text-slate-700"
                  >
                    Head teacher remarks
                  </label>
                  <textarea
                    id="head-teacher-remarks"
                    rows={4}
                    value={headRemarks}
                    onChange={(event) => setHeadRemarks(event.target.value)}
                    disabled={!canReleaseSelected}
                    className={remarksClassName}
                    placeholder={
                      canReleaseSelected
                        ? 'Add head teacher remarks before releasing'
                        : 'Remarks can be added when the student is ready for you'
                    }
                  />
                  <div className="flex flex-wrap items-center justify-end gap-3 pt-1">
                    <p className="text-xs text-slate-500">Head teacher</p>
                    {canReleaseSelected ? (
                      <Button
                        type="button"
                        className="max-w-fit py-2 text-sm"
                        loading={isReleasing}
                        loadingText="Releasing"
                        onClick={() =>
                          releaseStudents({
                            student_ids: [selectedStudent.id],
                            remarks: headRemarks.trim(),
                          })
                        }
                      >
                        Release
                      </Button>
                    ) : null}
                    {canGenerateReport ? (
                      <Button
                        type="button"
                        variant="outline"
                        className="max-w-fit py-2 text-sm"
                        onClick={() => toast('Report generation comes next.')}
                      >
                        Generate report
                      </Button>
                    ) : null}
                  </div>
                </div>
              </>
            )}
          </section>
        </div>
      )}

      <BulkReleaseModal
        open={bulkOpen}
        readyCount={readyIds.length}
        isSubmitting={isReleasing}
        onClose={() => setBulkOpen(false)}
        onConfirm={(remarks) => releaseStudents({ student_ids: readyIds, remarks })}
      />
    </div>
  )
}

export default AdminAssessmentDetail
