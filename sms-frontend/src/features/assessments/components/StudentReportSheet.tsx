import type { StudentReportPreview } from '@/features/classes/assessment/types'
import { mergeClasses } from '@/utils'

type StudentReportSheetProps = {
  data: StudentReportPreview
}

const formatScore = (value: number | null | undefined) => {
  if (value === null || value === undefined) return ''
  return Number.isInteger(value) ? String(value) : value.toFixed(2)
}

const formatTotalCell = (
  value: number | null | undefined,
  max: number | null | undefined,
) => {
  const score = formatScore(value)
  const highest = formatScore(max)
  if (!score && !highest) return ''
  if (!score) return highest ? `(${highest})` : ''
  if (!highest) return score
  return `${score} (${highest})`
}

const chunkBands = <T,>(items: T[], columns: number) => {
  if (items.length === 0) return []
  const size = Math.ceil(items.length / columns)
  return Array.from({ length: columns }, (_, index) =>
    items.slice(index * size, index * size + size),
  ).filter((column) => column.length > 0)
}

const labelClass = 'font-medium shrink-0'
const bodyClass = 'text-[13px] leading-relaxed'
const thClass = 'border border-black px-2 py-1.5 font-medium whitespace-nowrap'

type DottedFillProps = {
  value?: string | null
  className?: string
  minWidthClass?: string
  fullWidth?: boolean
}

const DottedFill = ({
  value,
  className,
  minWidthClass = 'min-w-[100px]',
  fullWidth = false,
}: DottedFillProps) => (
  <span
    className={mergeClasses(
      'border-b border-dotted border-black align-bottom',
      fullWidth ? 'block min-w-0 flex-1' : mergeClasses('inline-block', minWidthClass),
      value ? 'border-transparent' : 'pb-0.5',
      className,
    )}
  >
    {value || '\u00A0'}
  </span>
)

const InlineField = ({
  label,
  value,
  minWidthClass,
  fullWidth = false,
}: {
  label: string
  value?: string | null
  minWidthClass?: string
  fullWidth?: boolean
}) => (
  <p className={mergeClasses('flex items-end gap-x-1', fullWidth ? 'w-full' : 'flex-wrap')}>
    <span className={labelClass}>{label}</span>
    <DottedFill value={value} minWidthClass={minWidthClass} fullWidth={fullWidth} />
  </p>
)

const StudentReportSheet = ({ data }: StudentReportSheetProps) => {
  const caWeight = data.weights.continuous_assessment_weight
  const examWeight = data.weights.exam_weight
  const gradeColumns = chunkBands(data.grade_bands, 3)
  const { school } = data

  const contactLine = [
    school.box_address,
    school.address,
    school.phone_number ? `Tel: ${school.phone_number}` : '',
    school.phone_number_alt ? `Alt: ${school.phone_number_alt}` : '',
  ].filter(Boolean)

  return (
    <article
      className={`report-sheet mx-auto max-w-4xl bg-white px-8 py-8 text-black print:mx-0 print:max-w-none print:px-0 print:py-0 ${bodyClass}`}
    >
      <header className="relative mb-4 flex min-h-28 items-center">
        {school.logo_url ? (
          <img
            src={school.logo_url}
            alt=""
            className="absolute left-0 top-0 h-28 w-28 object-contain"
          />
        ) : null}
        <div className="w-full space-y-1 text-center text-xs font-medium">
          <h1 className="text-lg font-medium uppercase tracking-wide">{school.name}</h1>
          {contactLine.length > 0 ? <p>{contactLine.join(' • ')}</p> : null}
          {school.email ? <p>{school.email}</p> : null}
        </div>
      </header>

      <p className="mb-5 text-center text-sm font-semibold uppercase underline underline-offset-4">
        {data.report_title}
      </p>

      <section className="mb-5 border border-black p-3 text-[13px]">
        <div className="grid gap-3 md:grid-cols-2">
          <div className="space-y-1.5">
            <p>
              <span className={labelClass}>Student&apos;s Name:</span> {data.student_name}
            </p>
            <p>
              <span className={labelClass}>Class:</span> {data.class_name}
            </p>
            <p>
              <span className={labelClass}>Academic Year:</span> {data.academic_year}
            </p>
            <p>
              <span className={labelClass}>Term:</span> {data.term_label}
            </p>
          </div>
          <div className="space-y-1.5">
            <InlineField label="Next Term Begins:" value={data.next_term_begins} />
            <p>
              <span className={labelClass}>No. On Roll:</span> {data.students_on_roll}
            </p>
            {data.uses_position ? (
              <InlineField label="Position:" value={data.position_label} minWidthClass="min-w-[60px]" />
            ) : null}
          </div>
        </div>
      </section>

      <table className="mb-5 w-full border-collapse border border-black text-[12px]">
        <thead>
          <tr>
            <th className={`${thClass} text-left`}>Subject</th>
            <th className={`${thClass} text-center`}>Class Score ({caWeight})</th>
            <th className={`${thClass} text-center`}>Exams Score ({examWeight})</th>
            <th className={`${thClass} text-center`}>Total Score</th>
            {data.uses_grades ? <th className={`${thClass} text-center`}>Grade</th> : null}
            <th className={`${thClass} text-left`}>Remarks</th>
          </tr>
        </thead>
        <tbody>
          {data.subjects.map((subject) => (
            <tr key={subject.subject_label}>
              <td className="border border-black px-2 py-1.5 font-medium capitalize">
                {subject.subject_label}
              </td>
              <td className="border border-black px-2 py-1.5 text-center">
                {formatScore(subject.class_score)}
              </td>
              <td className="border border-black px-2 py-1.5 text-center">
                {formatScore(subject.exam_score)}
              </td>
              <td className="border border-black px-2 py-1.5 text-center">
                {formatScore(subject.total)}
              </td>
              {data.uses_grades ? (
                <td className="border border-black px-2 py-1.5 text-center">
                  {subject.grade ?? ''}
                </td>
              ) : null}
              <td className="border border-black px-2 py-1.5 capitalize">
                {subject.remark ?? ''}
              </td>
            </tr>
          ))}
          <tr className="font-medium">
            <td className="border border-black px-2 py-1.5">Total</td>
            <td className="border border-black px-2 py-1.5 text-center">
              {formatTotalCell(data.totals.class_score, data.totals.max_class_score)}
            </td>
            <td className="border border-black px-2 py-1.5 text-center">
              {formatTotalCell(data.totals.exam_score, data.totals.max_exam_score)}
            </td>
            <td className="border border-black px-2 py-1.5 text-center">
              {formatTotalCell(data.totals.total, data.totals.max_total)}
            </td>
            {data.uses_grades ? (
              <td className="border border-black px-2 py-1.5 text-center" />
            ) : null}
            <td className="border border-black px-2 py-1.5" />
          </tr>
        </tbody>
      </table>

      <section className="mb-5 space-y-2 text-[13px]">
        <p className="flex flex-wrap items-end justify-center gap-x-1 font-medium">
          <span>Attendance:</span>
          <DottedFill minWidthClass="min-w-[72px]" />
          <span>of</span>
          <DottedFill minWidthClass="min-w-[72px]" />
        </p>
        <InlineField label="Conduct:" value={data.conduct || null} fullWidth />
        <InlineField label="Attitude:" value={data.attitude || null} fullWidth />
        <InlineField label="Interest:" value={data.interest || null} fullWidth />
        <InlineField
          label="Class Teacher's Remarks:"
          value={data.class_teacher_remarks || null}
          minWidthClass="min-w-[240px]"
        />
        <InlineField
          label="Headteacher's Remarks:"
          value={data.head_teacher_remarks || null}
          minWidthClass="min-w-[240px]"
        />
      </section>

      <footer className="grid gap-6 pt-6 md:grid-cols-2 text-[13px]">
        <div className="text-center">
          <div className="mb-2 border-b border-dotted border-black pb-8" />
          <p className="font-medium">(Class Teacher&apos;s Signature)</p>
          {data.class_teacher_name ? (
            <p className="mt-1 text-xs capitalize">{data.class_teacher_name}</p>
          ) : null}
        </div>
        <div className="text-center">
          <div className="mb-2 border-b border-dotted border-black pb-8" />
          <p className="font-medium">(Headteacher&apos;s Signature)</p>
        </div>
      </footer>

      {data.uses_grades && data.grade_bands.length > 0 ? (
        <section className="mt-6">
          <h2 className="mb-2 text-center text-xs font-medium italic underline underline-offset-4">
            Grades Interpretation
          </h2>
          <div className="grid gap-3 border border-black p-3 md:grid-cols-3 text-[11px]">
            {gradeColumns.map((column, columnIndex) => (
              <div key={columnIndex} className="space-y-1.5">
                {column.map((band) => (
                  <p key={`${band.grade}-${band.min_score}`} className="capitalize">
                    <span className="font-medium">Grade {band.grade}:</span> {band.min_score}-
                    {band.max_score} ({band.remark})
                  </p>
                ))}
              </div>
            ))}
          </div>
        </section>
      ) : null}
    </article>
  )
}

export default StudentReportSheet
