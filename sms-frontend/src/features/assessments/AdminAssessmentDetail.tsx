import { useEffect, useMemo, useRef, useState } from 'react'
import { Icon } from '@iconify/react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'
import ActionBar from '@/components/shared/ActionBar'
import { Table, TableWrapper } from '@/components/shared'
import { Button } from '@/components/ui'
import { Capability } from '@/features/auth/capabilities'
import { useCan } from '@/features/auth/hooks'
import {
  adminCorrectStudent,
  getAdminAssessmentDetail,
  getBulkReportGenerateJob,
  queueBulkReportGenerate,
  releaseAdminAssessmentStudents,
  reviewAdminCorrection,
} from '@/features/classes/services'
import type {
  AdminAssessmentDetailStudent,
  AdminAssessmentStudentStatus,
  ReportGenerateJob,
} from '@/features/classes/assessment/types'
import { getApiErrorMessage, mergeClasses } from '@/utils'
import BulkReleaseModal from './components/BulkReleaseModal'
import CorrectionModal from './components/CorrectionModal'
import ReportReadyModal from './components/ReportReadyModal'

type StatusFilter = 'all' | 'ready_for_you' | 'released' | 'needs_correction'

const statusLabel = (status: AdminAssessmentStudentStatus) => {
  if (status === 'ready_for_you') return 'Ready for you'
  if (status === 'released') return 'Released'
  if (status === 'needs_correction') return 'Needs correction'
  return 'With class teacher'
}

const statusChipClass = (status: AdminAssessmentStudentStatus) =>
  mergeClasses(
    'inline-flex rounded-md px-2 py-0.5 text-xs font-medium',
    status === 'released' && 'bg-emerald-50 text-emerald-800',
    status === 'ready_for_you' && 'bg-blue-50 text-blue-800',
    status === 'needs_correction' && 'bg-orange-50 text-orange-800',
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
  const navigate = useNavigate()
  const [searchParams] = useSearchParams()
  const termId = searchParams.get('term') ?? undefined
  const queryClient = useQueryClient()
  const canRelease = useCan(Capability.ASSESSMENTS_RELEASE)

  const [statusFilter, setStatusFilter] = useState<StatusFilter>('all')
  const [selectedStudentId, setSelectedStudentId] = useState<string | null>(null)
  const [remarksByStudent, setRemarksByStudent] = useState<Record<string, string>>({})
  const [bulkOpen, setBulkOpen] = useState(false)
  const [correctionOpen, setCorrectionOpen] = useState(false)
  const [notifyOpen, setNotifyOpen] = useState(false)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(() => new Set())
  const [generateJobId, setGenerateJobId] = useState<string | null>(null)
  const toastedJobId = useRef<string | null>(null)

  const { data, isLoading, isError, error } = useQuery({
    queryKey: DETAIL_QUERY_KEY(streamId ?? '', termId ?? ''),
    queryFn: () => getAdminAssessmentDetail(streamId!, termId),
    enabled: Boolean(streamId),
  })

  const { data: generateJob } = useQuery({
    queryKey: ['assessments', 'admin', 'report-generate-job', streamId, generateJobId],
    queryFn: () => getBulkReportGenerateJob(streamId!, generateJobId!),
    enabled: Boolean(streamId && generateJobId),
    refetchInterval: (query) => {
      const job = query.state.data as ReportGenerateJob | undefined
      if (!job || job.done) return false
      return 3000
    },
  })

  useEffect(() => {
    if (!generateJob?.done || !generateJobId) return
    if (toastedJobId.current === generateJobId) return
    toastedJobId.current = generateJobId
    toast.success(
      `Reports finished: ${generateJob.generated} generated, ${generateJob.skipped} already had a file, ${generateJob.failed} failed.`,
    )
    queryClient.invalidateQueries({
      queryKey: DETAIL_QUERY_KEY(streamId ?? '', termId ?? ''),
    })
  }, [generateJob, generateJobId, queryClient, streamId, termId])

  const filteredStudents = useMemo(() => {
    const students = data?.students ?? []
    if (statusFilter === 'all') return students
    return students.filter((student) => student.status === statusFilter)
  }, [data?.students, statusFilter])

  const resolvedStudentId = (() => {
    if (!filteredStudents.length) return null
    if (
      selectedStudentId &&
      filteredStudents.some((student) => student.id === selectedStudentId)
    ) {
      return selectedStudentId
    }
    const preferred =
      filteredStudents.find((student) => student.status === 'ready_for_you') ??
      filteredStudents[0]
    return preferred.id
  })()

  const selectedStudent: AdminAssessmentDetailStudent | null =
    resolvedStudentId
      ? (data?.students.find((student) => student.id === resolvedStudentId) ?? null)
      : null

  const headRemarks = selectedStudent
    ? (remarksByStudent[selectedStudent.id] ?? selectedStudent.head_teacher_remarks ?? '')
    : ''

  const setHeadRemarks = (value: string) => {
    if (!selectedStudent) return
    setRemarksByStudent((current) => ({ ...current, [selectedStudent.id]: value }))
  }

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

  const { mutate: correctStudent, isPending: isCorrecting } = useMutation({
    mutationFn: (payload: { teaching_assignment_ids: string[]; reason: string }) =>
      adminCorrectStudent(streamId!, resolvedStudentId!, payload, termId),
    onSuccess: (payload) => {
      toast.success(
        payload.correction.kind === 'reopen'
          ? 'Results reopened for correction'
          : 'Subjects sent back for correction',
      )
      queryClient.setQueryData(DETAIL_QUERY_KEY(streamId ?? '', termId ?? ''), payload.detail)
      setCorrectionOpen(false)
    },
    onError: (err) => toast.error(getApiErrorMessage(err, 'Unable to send back subjects')),
  })

  const { mutate: reviewCorrection, isPending: isReviewing } = useMutation({
    mutationFn: (approve: boolean) =>
      reviewAdminCorrection(
        streamId!,
        selectedStudent!.active_correction!.id,
        approve,
        termId,
      ),
    onSuccess: (payload, approve) => {
      toast.success(approve ? 'Reopen approved' : 'Reopen request declined')
      queryClient.setQueryData(DETAIL_QUERY_KEY(streamId ?? '', termId ?? ''), payload.detail)
    },
    onError: (err) => toast.error(getApiErrorMessage(err, 'Unable to review request')),
  })

  const readyIds =
    data?.students.filter((student) => student.status === 'ready_for_you').map((student) => student.id) ??
    []

  const canManageReports = canRelease
  const isReleased = (student: AdminAssessmentDetailStudent) => student.status === 'released'
  const isNotifyEligible = (student: AdminAssessmentDetailStudent) =>
    isReleased(student) && Boolean(student.has_report)
  const needsReport = (student: AdminAssessmentDetailStudent) =>
    isReleased(student) && !student.has_report

  const releasedIds = useMemo(
    () => (data?.students ?? []).filter(isReleased).map((student) => student.id),
    [data?.students],
  )

  const selectedCount = selectedIds.size
  const selectedList = useMemo(() => Array.from(selectedIds), [selectedIds])
  const selectedForGenerate = useMemo(
    () =>
      selectedList.filter((id) => {
        const student = data?.students.find((row) => row.id === id)
        return student ? needsReport(student) : false
      }),
    [selectedList, data?.students],
  )
  const selectedForNotify = useMemo(
    () =>
      selectedList.filter((id) => {
        const student = data?.students.find((row) => row.id === id)
        return student ? isNotifyEligible(student) : false
      }),
    [selectedList, data?.students],
  )

  const toggleSelectedRow = (studentId: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(studentId)) next.delete(studentId)
      else next.add(studentId)
      return next
    })
  }

  const clearSelection = () => setSelectedIds(new Set())

  const selectAllReleased = () => setSelectedIds(new Set(releasedIds))

  const { mutate: startBulkGenerate, isPending: isQueueingGenerate } = useMutation({
    mutationFn: (studentIds: string[]) =>
      queueBulkReportGenerate(
        streamId!,
        {
          student_ids: studentIds,
          term_id: termId,
          force: false,
        },
        termId,
      ),
    onSuccess: (job) => {
      toast.success(
        `Generating reports in the background (${job.total} student${job.total === 1 ? '' : 's'}).`,
      )
      setGenerateJobId(job.id)
    },
    onError: (err) => toast.error(getApiErrorMessage(err, 'Unable to start report generation')),
  })

  const generateJobRunning = Boolean(generateJobId) && !generateJob?.done

  const pillTabs: Array<{ key: StatusFilter; label: string; count: number }> = [
    { key: 'all', label: 'All', count: data?.students_count ?? 0 },
    { key: 'ready_for_you', label: 'Ready for you', count: data?.ready_for_you_count ?? 0 },
    { key: 'released', label: 'Released', count: data?.released_count ?? 0 },
    {
      key: 'needs_correction',
      label: 'Needs correction',
      count: data?.needs_correction_count ?? 0,
    },
  ]

  const weights = data?.weights
  const canReleaseSelected = selectedStudent?.status === 'ready_for_you' && canRelease
  const canGenerateReport = selectedStudent?.status === 'released'
  const canNotifySelected =
    Boolean(canManageReports && selectedStudent && isNotifyEligible(selectedStudent))
  const canCorrectSelected =
    canRelease &&
    selectedStudent &&
    (selectedStudent.status === 'ready_for_you' ||
      selectedStudent.status === 'released' ||
      selectedStudent.status === 'needs_correction')
  const pendingReopen =
    selectedStudent?.active_correction?.kind === 'reopen_request' &&
    selectedStudent.active_correction.status === 'open'
  const activeCorrection = selectedStudent?.active_correction

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
        <div className="space-y-4">
          <div className="bg-white p-4 custom-shadow-md space-y-4">
            <div className="min-w-0">
              <h2 className="text-lg font-medium text-slate-900">{data.display_name}</h2>
              <p className="text-sm text-slate-500 mt-0.5">
                {data.class_teacher_name ?? 'No class teacher'}
                <span className="mx-1.5 text-slate-300">·</span>
                {data.term_label}
              </p>
              {data.with_class_teacher_count > 0 ? (
                <p className="text-xs text-slate-400 mt-1">
                  {data.with_class_teacher_count} still with the class teacher — not shown
                </p>
              ) : null}
              {(data.pending_reopen_requests_count ?? 0) > 0 ? (
                <p className="text-xs text-orange-700 mt-1">
                  {data.pending_reopen_requests_count} reopen request
                  {data.pending_reopen_requests_count === 1 ? '' : 's'} awaiting review
                </p>
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
          </div>

          <div className="grid grid-cols-1 gap-4 xl:grid-cols-12 min-h-[70vh]">
          <aside className="xl:col-span-4 bg-white p-4 custom-shadow-md flex flex-col gap-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
              {canManageReports && releasedIds.length > 0 ? (
                <Button
                  type="button"
                  variant="outline"
                  className="max-w-fit py-1.5 text-sm"
                  onClick={selectAllReleased}
                >
                  Select all released ({releasedIds.length})
                </Button>
              ) : (
                <span className="text-xs text-slate-500">Student list</span>
              )}
              {canRelease && readyIds.length > 0 ? (
                <Button
                  type="button"
                  variant="outline"
                  className="max-w-fit py-1.5 text-sm"
                  onClick={() => setBulkOpen(true)}
                >
                  Release all ready ({readyIds.length})
                </Button>
              ) : null}
            </div>

            {canManageReports && generateJobRunning ? (
              <div className="rounded-md border border-sky-200 bg-sky-50 px-3 py-2 text-sm text-sky-900">
                Generating reports…
                {generateJob ? (
                  <span className="ml-1">
                    {generateJob.generated + generateJob.skipped + generateJob.failed}/
                    {generateJob.total}
                    {generateJob.failed > 0 ? ` (${generateJob.failed} failed so far)` : ''}
                  </span>
                ) : null}
              </div>
            ) : null}

            {canManageReports && selectedCount > 0 ? (
              <div className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-slate-200 bg-slate-50 px-3 py-2">
                <p className="text-sm text-slate-700">
                  <span className="font-medium text-slate-900">{selectedCount}</span> selected
                  <button
                    type="button"
                    className="ml-2 text-sm text-sky-700 hover:underline"
                    onClick={clearSelection}
                  >
                    Clear
                  </button>
                </p>
                <div className="flex flex-wrap items-center gap-2">
                  <Button
                    type="button"
                    variant="outline"
                    className="max-w-fit py-1.5 text-sm"
                    loading={isQueueingGenerate}
                    loadingText="Queuing…"
                    disabled={
                      selectedForGenerate.length === 0 || generateJobRunning || isQueueingGenerate
                    }
                    onClick={() => startBulkGenerate(selectedForGenerate)}
                  >
                    <Icon icon="hugeicons:file-02" className="size-4" />
                    Generate reports
                    {selectedForGenerate.length > 0 ? ` (${selectedForGenerate.length})` : ''}
                  </Button>
                  <Button
                    type="button"
                    className="max-w-fit py-1.5 text-sm"
                    disabled={selectedForNotify.length === 0}
                    onClick={() => setNotifyOpen(true)}
                  >
                    <Icon icon="hugeicons:mail-01" className="size-4" />
                    Send to guardians
                    {selectedForNotify.length > 0 ? ` (${selectedForNotify.length})` : ''}
                  </Button>
                </div>
              </div>
            ) : null}

            <ul className="space-y-2 overflow-y-auto">
              {filteredStudents.length === 0 ? (
                <li className="text-sm text-slate-500 py-6 text-center">
                  No students are ready for review yet.
                </li>
              ) : (
                filteredStudents.map((student) => {
                  const selected = student.id === resolvedStudentId
                  const released = isReleased(student)
                  return (
                    <li key={student.id}>
                      <div
                        className={mergeClasses(
                          'flex items-start gap-2 rounded-lg border px-3 py-3 transition-colors',
                          selected
                            ? 'border-slate-900 bg-slate-50'
                            : 'border-slate-200 bg-white hover:border-slate-300',
                        )}
                      >
                        {canManageReports && released ? (
                          <input
                            type="checkbox"
                            className="mt-1 size-4 shrink-0 rounded border-slate-300 text-slate-900 focus:ring-slate-400"
                            checked={selectedIds.has(student.id)}
                            onChange={() => toggleSelectedRow(student.id)}
                            onClick={(event) => event.stopPropagation()}
                            aria-label={`Select ${student.full_name}`}
                          />
                        ) : canManageReports ? (
                          <span className="mt-1 size-4 shrink-0" aria-hidden />
                        ) : null}
                        <button
                          type="button"
                          onClick={() => setSelectedStudentId(student.id)}
                          className="min-w-0 flex-1 text-left cursor-pointer"
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div className="min-w-0">
                              <p className="text-sm font-medium text-slate-900 truncate">
                                {student.full_name}
                              </p>
                              <p className="text-xs text-slate-500 mt-0.5">{student.student_id}</p>
                            </div>
                            <div className="flex shrink-0 flex-col items-end gap-1">
                              <span className={statusChipClass(student.status)}>
                                {statusLabel(student.status)}
                              </span>
                              {student.has_report ? (
                                <span className="inline-flex rounded-md bg-emerald-50 px-2 py-0.5 text-[10px] font-medium text-emerald-800">
                                  Report generated
                                </span>
                              ) : null}
                              {student.active_correction?.kind === 'reopen_request' &&
                              student.active_correction.status === 'open' ? (
                                <span className="inline-flex rounded-md bg-orange-50 px-2 py-0.5 text-[10px] font-medium text-orange-800">
                                  Reopen requested
                                </span>
                              ) : null}
                            </div>
                          </div>
                        </button>
                      </div>
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

                {activeCorrection ? (
                  <div className="rounded-lg border border-orange-200 bg-orange-50 px-3 py-3 text-sm text-orange-950">
                    <p className="font-medium">
                      {pendingReopen
                        ? 'Reopen requested'
                        : activeCorrection.status === 'applied'
                          ? 'Correction in progress'
                          : 'Correction'}
                    </p>
                    <p className="mt-1 text-orange-900/90">{activeCorrection.reason}</p>
                    <p className="mt-1 text-xs text-orange-800/80">
                      Subjects:{' '}
                      {activeCorrection.subjects.map((subject) => subject.subject_label).join(', ')}
                    </p>
                    {pendingReopen && canRelease ? (
                      <div className="mt-3 flex flex-wrap gap-2">
                        <Button
                          type="button"
                          className="max-w-fit py-2 text-sm"
                          loading={isReviewing}
                          loadingText="Saving"
                          onClick={() => reviewCorrection(true)}
                        >
                          Approve reopen
                        </Button>
                        <Button
                          type="button"
                          variant="outline"
                          className="max-w-fit py-2 text-sm"
                          disabled={isReviewing}
                          onClick={() => reviewCorrection(false)}
                        >
                          Decline
                        </Button>
                      </div>
                    ) : null}
                  </div>
                ) : null}

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
                                {subject.position !== null && subject.position !== undefined
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
                    {selectedStudent.overall_position !== null &&
                    selectedStudent.overall_position !== undefined &&
                    selectedStudent.overall_cohort_size !== null &&
                    selectedStudent.overall_cohort_size !== undefined ? (
                      <p>
                        Overall position:{' '}
                        <span className="font-medium text-slate-900">
                          {formatOrdinal(selectedStudent.overall_position)} of{' '}
                          {selectedStudent.overall_cohort_size}
                        </span>
                        {selectedStudent.overall_average !== null &&
                        selectedStudent.overall_average !== undefined ? (
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

                <div className="space-y-4">
                  {(
                    [
                      { id: 'conduct', label: 'Conduct', value: selectedStudent.conduct },
                      { id: 'attitude', label: 'Attitude', value: selectedStudent.attitude },
                      { id: 'interest', label: 'Interest', value: selectedStudent.interest },
                    ] as const
                  ).map((field) => (
                    <div key={field.id} className="space-y-2">
                      <label
                        htmlFor={`admin-${field.id}`}
                        className="block text-sm font-medium text-slate-700"
                      >
                        {field.label}
                      </label>
                      <input
                        id={`admin-${field.id}`}
                        type="text"
                        value={field.value || '—'}
                        readOnly
                        disabled
                        className={remarksClassName}
                      />
                    </div>
                  ))}

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
                          onClick={() => {
                            const term = termId ? `?term=${termId}` : ''
                            navigate(
                              `/assessments/classes/${streamId}/report/${selectedStudent.id}${term}`,
                            )
                          }}
                        >
                          {selectedStudent.has_report ? 'View report' : 'Generate report'}
                        </Button>
                      ) : null}
                      {canNotifySelected ? (
                        <Button
                          type="button"
                          variant="outline"
                          className="max-w-fit py-2 text-sm"
                          onClick={() => {
                            setSelectedIds(new Set([selectedStudent.id]))
                            setNotifyOpen(true)
                          }}
                        >
                          Send to guardians
                        </Button>
                      ) : null}
                      {canCorrectSelected ? (
                        <Button
                          type="button"
                          variant="outline"
                          color="red"
                          className="max-w-fit py-2 text-sm"
                          onClick={() => setCorrectionOpen(true)}
                        >
                          {selectedStudent.status === 'released'
                            ? 'Reopen subjects'
                            : 'Send back subjects'}
                        </Button>
                      ) : null}
                    </div>
                  </div>
                </div>
              </>
            )}
          </section>
          </div>
        </div>
      )}

      <BulkReleaseModal
        open={bulkOpen}
        readyCount={readyIds.length}
        isSubmitting={isReleasing}
        onClose={() => setBulkOpen(false)}
        onConfirm={(remarks) => releaseStudents({ student_ids: readyIds, remarks })}
      />

      <CorrectionModal
        open={correctionOpen}
        title={
          selectedStudent?.status === 'released'
            ? 'Reopen subjects'
            : 'Send subjects back'
        }
        description={
          selectedStudent?.status === 'released'
            ? 'Select subjects to reopen. The stored report PDF will be deleted until results are released again.'
            : 'Select published subjects to return to the subject teacher, and explain why.'
        }
        confirmLabel={selectedStudent?.status === 'released' ? 'Reopen' : 'Send back'}
        subjects={selectedStudent?.subjects ?? []}
        isSubmitting={isCorrecting}
        onClose={() => setCorrectionOpen(false)}
        onConfirm={(payload) => correctStudent(payload)}
      />

      {canManageReports && streamId ? (
        <ReportReadyModal
          open={notifyOpen}
          streamId={streamId}
          termId={termId}
          studentIds={selectedForNotify}
          onClose={() => setNotifyOpen(false)}
          onSent={clearSelection}
        />
      ) : null}
    </div>
  )
}

export default AdminAssessmentDetail
