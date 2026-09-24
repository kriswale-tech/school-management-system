import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { Table, TableWrapper } from '@/components/shared'
import DotComponent from '@/components/ui/DotComponent'
import FilterComponent, { type FilterSelection } from '@/components/ui/FilterComponent'
import StudentReportViewer from '@/features/assessments/components/StudentReportViewer'
import type { AdminAssessmentStudentStatus } from '@/features/classes/assessment/types'
import { getApiErrorMessage, mergeClasses } from '@/utils'
import {
  generateStudentAssessmentReport,
  getStudentAssessmentReport,
  getStudentAssessments,
} from '../../services'
import {
  STUDENT_ASSESSMENTS_QUERY_KEY,
  STUDENT_ASSESSMENTS_REPORT_QUERY_KEY,
} from '../../utils'

type AssessmentProps = {
  studentId: string
}

const statusLabel = (status: AdminAssessmentStudentStatus) => {
  if (status === 'ready_for_you') return 'Awaiting release'
  if (status === 'released') return 'Released'
  if (status === 'needs_correction') return 'Needs correction'
  return 'In progress'
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
  'w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 outline-none disabled:cursor-not-allowed disabled:bg-slate-50 disabled:text-slate-500'

const Assessment = ({ studentId }: AssessmentProps) => {
  const [termSelection, setTermSelection] = useState<FilterSelection | undefined>(undefined)

  const queryParams = useMemo(
    () => ({
      term: termSelection === undefined || termSelection === '' ? undefined : String(termSelection),
    }),
    [termSelection],
  )

  const { data, isLoading, isError, error } = useQuery({
    queryKey: [STUDENT_ASSESSMENTS_QUERY_KEY, studentId, queryParams],
    queryFn: () => getStudentAssessments(studentId, queryParams),
    enabled: Boolean(studentId),
  })

  const term: FilterSelection =
    termSelection !== undefined && termSelection !== ''
      ? termSelection
      : (data?.term_id ?? '')

  const termOptions = (data?.terms ?? []).map((item) => ({
    value: item.id,
    label: item.label,
  }))

  const student = data?.student ?? null
  const weights = data?.weights

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="min-w-0 flex flex-wrap items-center">
          {data?.enrolled && student ? (
            <>
              <h3 className="text-lg font-medium text-slate-900">
                {data.display_name ?? 'Class assessment'}
              </h3>
              <DotComponent />
              <span className="text-sm text-slate-500">
                {data.class_teacher_name ?? 'No class teacher'}
              </span>
              {data.term_label ? (
                <>
                  <DotComponent />
                  <span className="text-sm text-slate-500">{data.term_label}</span>
                </>
              ) : null}
            </>
          ) : null}
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {data?.enrolled && student ? (
            <span className={statusChipClass(student.status)}>{statusLabel(student.status)}</span>
          ) : null}
          <FilterComponent
            filterName="Term"
            filterKey="student_assessments_term"
            options={termOptions}
            value={term}
            placeholder={isLoading && !data ? 'Loading…' : 'Academic Year & Term'}
            onChange={setTermSelection}
          />
        </div>
      </div>

      {!data && isLoading ? (
        <p className="text-sm text-slate-500 py-6">Loading assessment…</p>
      ) : isError || !data ? (
        <p className="text-sm text-red-600 py-6" role="alert">
          {getApiErrorMessage(error, 'Unable to load student assessment.')}
        </p>
      ) : !data.enrolled || !student ? (
        <p className="text-sm text-slate-500 py-6">
          {data.terms.length === 0
            ? 'This student has no class enrollment for reports yet.'
            : 'This student is not enrolled in the selected term.'}
        </p>
      ) : (
        <div className="space-y-6">
          <TableWrapper
            isEmpty={student.subjects.length === 0}
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
                      Exams score{' '}
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
                  </Table.Row>
                </Table.Head>
                <Table.Body>
                  {student.subjects.map((subject) => (
                    <Table.Row key={`${student.id}-${subject.subject_label}`}>
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
                    </Table.Row>
                  ))}
                </Table.Body>
              </Table>
            </div>
          </TableWrapper>

          {data.uses_position ? (
            <div className="rounded-lg border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-slate-700">
              {student.overall_position != null && student.overall_cohort_size != null ? (
                <p>
                  Overall position:{' '}
                  <span className="font-medium text-slate-900">
                    {formatOrdinal(student.overall_position)} of {student.overall_cohort_size}
                  </span>
                  {student.overall_average != null ? (
                    <span className="text-slate-500">
                      {' '}
                      · Average {formatScore(student.overall_average)}%
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
                { id: 'conduct', label: 'Conduct', value: student.conduct },
                { id: 'attitude', label: 'Attitude', value: student.attitude },
                { id: 'interest', label: 'Interest', value: student.interest },
              ] as const
            ).map((field) => (
              <div key={field.id} className="space-y-2">
                <label
                  htmlFor={`student-${field.id}`}
                  className="block text-sm font-medium text-slate-700"
                >
                  {field.label}
                </label>
                <input
                  id={`student-${field.id}`}
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
                htmlFor="student-class-teacher-remarks"
                className="block text-sm font-medium text-slate-700"
              >
                Class teacher remarks
              </label>
              <textarea
                id="student-class-teacher-remarks"
                rows={3}
                value={student.class_teacher_remarks}
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
                htmlFor="student-head-teacher-remarks"
                className="block text-sm font-medium text-slate-700"
              >
                Head teacher remarks
              </label>
              <textarea
                id="student-head-teacher-remarks"
                rows={4}
                value={student.head_teacher_remarks}
                readOnly
                disabled
                className={remarksClassName}
                placeholder="No head teacher remarks yet"
              />
              <div className="flex justify-end">
                <p className="text-xs text-slate-500">Head teacher</p>
              </div>
            </div>
          </div>

          {student.status === 'released' && data.term_id ? (
            <StudentReportViewer
              variant="embed"
              autoLoad={false}
              enabled
              queryKey={[STUDENT_ASSESSMENTS_REPORT_QUERY_KEY, studentId, data.term_id]}
              getReport={() =>
                getStudentAssessmentReport(studentId, { term: data.term_id ?? undefined })
              }
              generateReport={() =>
                generateStudentAssessmentReport(studentId, { term: data.term_id ?? undefined })
              }
            />
          ) : null}
        </div>
      )}
    </div>
  )
}

export default Assessment
