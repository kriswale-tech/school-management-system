import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import FilterComponent, { type FilterSelection } from '@/components/ui/FilterComponent'
import ChartCard from '@/features/reports/components/ChartCard'
import GradePieChart from '@/features/reports/components/GradePieChart'
import {
  CHART_GRID,
  CHART_SERIES,
  CHART_SKY,
  CHART_TICK,
  formatScore,
} from '@/features/reports/utils'
import { getApiErrorMessage } from '@/utils'
import { getStudentPerformance } from '../../services'
import type { StudentPerformanceSubject, SubjectRating } from '../../types'
import { STUDENT_PERFORMANCE_QUERY_KEY } from '../../utils'

type PerformanceProps = {
  studentId: string
}

const ALL_TIME = 'all_time'

const ratingLabel = (rating: SubjectRating) => {
  if (rating === 'strong') return 'Strong'
  if (rating === 'secure') return 'Secure'
  if (rating === 'borderline') return 'Borderline'
  return 'At risk'
}

const ratingClass = (rating: SubjectRating) => {
  if (rating === 'strong') return 'text-emerald-700'
  if (rating === 'secure') return 'text-sky-700'
  if (rating === 'borderline') return 'text-amber-700'
  return 'text-rose-700'
}

const RankingList = ({
  subjects,
  scoreCaption,
}: {
  subjects: StudentPerformanceSubject[]
  scoreCaption: string
}) => {
  if (subjects.length === 0) {
    return (
      <p className="py-4 text-sm text-slate-500">No published subject scores to rank yet.</p>
    )
  }

  return (
    <ul className="divide-y divide-slate-100">
      {subjects.map((subject) => (
        <li
          key={`${subject.rank}-${subject.subject_name}`}
          className="flex items-start justify-between gap-3 py-2.5"
        >
          <div className="min-w-0">
            <p className="text-sm text-slate-800">
              <span className="mr-2 font-semibold text-slate-500">#{subject.rank}</span>
              {subject.subject_name}
            </p>
            {subject.incomplete ? (
              <p className="mt-0.5 text-xs text-amber-700">
                Missing from {Math.max((subject.terms_enrolled ?? 0) - (subject.terms_with_score ?? 0), 0)}{' '}
                term
                {(subject.terms_enrolled ?? 0) - (subject.terms_with_score ?? 0) === 1 ? '' : 's'}
              </p>
            ) : null}
          </div>
          <div className="shrink-0 text-right">
            <p className="text-sm font-semibold text-slate-900">
              {formatScore(subject.total)}
              {subject.grade ? (
                <span className="ml-1 text-xs font-medium text-slate-500">({subject.grade})</span>
              ) : null}
            </p>
            <p className={`text-xs ${ratingClass(subject.rating)}`}>
              {ratingLabel(subject.rating)}
              <span className="text-slate-400"> · {scoreCaption}</span>
            </p>
          </div>
        </li>
      ))}
    </ul>
  )
}

const Performance = ({ studentId }: PerformanceProps) => {
  const [gradeTermSelection, setGradeTermSelection] = useState<FilterSelection | undefined>(
    undefined,
  )
  const [rankingSelection, setRankingSelection] = useState<FilterSelection>(ALL_TIME)

  const { data, isLoading, isError, error } = useQuery({
    queryKey: [STUDENT_PERFORMANCE_QUERY_KEY, studentId],
    queryFn: () => getStudentPerformance(studentId),
    enabled: Boolean(studentId),
  })

  const terms = useMemo(() => data?.terms ?? [], [data?.terms])
  const resolvedGradeTermId =
    gradeTermSelection !== undefined && gradeTermSelection !== ''
      ? String(gradeTermSelection)
      : (terms[terms.length - 1]?.term_id ?? '')

  const selectedGradeTerm = useMemo(
    () => terms.find((term) => term.term_id === resolvedGradeTermId) ?? terms[terms.length - 1],
    [terms, resolvedGradeTermId],
  )

  const rankingOptions = useMemo(
    () => [
      { value: ALL_TIME, label: 'All time' },
      ...terms.map((term) => ({ value: term.term_id, label: term.term_label })),
    ],
    [terms],
  )

  const resolvedRankingKey =
    rankingSelection !== '' &&
    rankingOptions.some((option) => option.value === String(rankingSelection))
      ? String(rankingSelection)
      : ALL_TIME

  const isAllTimeRanking = resolvedRankingKey === ALL_TIME
  const rankingTerm = useMemo(
    () => (isAllTimeRanking ? null : terms.find((term) => term.term_id === resolvedRankingKey)),
    [isAllTimeRanking, terms, resolvedRankingKey],
  )
  const rankedSubjects = isAllTimeRanking
    ? (data?.all_time_ranking ?? [])
    : (rankingTerm?.subjects ?? [])

  const subjectChartData = useMemo(() => {
    if (!data) return []
    const termLabels = data.overall_trend.map((point) => point.term_label)
    return termLabels.map((termLabel) => {
      const row: Record<string, string | number> = { term_label: termLabel }
      for (const trend of data.subject_trends) {
        const point = trend.points.find((item) => item.term_label === termLabel)
        if (point) row[trend.subject_name] = point.total
      }
      return row
    })
  }, [data])

  const subjectNames = data?.subject_trends.map((item) => item.subject_name) ?? []

  if (isLoading) {
    return <p className="text-sm text-slate-500 py-6">Loading performance…</p>
  }

  if (isError || !data) {
    return (
      <p className="text-sm text-red-600 py-6" role="alert">
        {getApiErrorMessage(error, 'Unable to load performance.')}
      </p>
    )
  }

  if (terms.length === 0) {
    return (
      <p className="text-sm text-slate-500 py-6">
        No enrollments yet — performance appears after the student is enrolled and scores are
        published.
      </p>
    )
  }

  const gradeMode = selectedGradeTerm?.mode ?? 'grades'
  const gradeIsScoreBands = gradeMode === 'score_bands'

  return (
    <div className="space-y-4">
      <ChartCard
        title="Overall average by term"
        description="Average across published subjects for each enrolled term."
        empty={data.overall_trend.length === 0}
        emptyTitle="No published scores yet"
        emptyDescription="Scores appear here once subjects are published for this student."
      >
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data.overall_trend} margin={{ top: 12, right: 12, left: 0, bottom: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID} vertical={false} />
            <XAxis
              dataKey="term_label"
              tick={{ fill: CHART_TICK, fontSize: 11 }}
              interval="preserveStartEnd"
            />
            <YAxis domain={[0, 100]} tick={{ fill: CHART_TICK, fontSize: 12 }} width={36} />
            <Tooltip formatter={(value) => formatScore(Number(value))} />
            <Line
              type="monotone"
              dataKey="average_score"
              stroke={CHART_SKY}
              strokeWidth={2}
              dot={{ r: 3 }}
            />
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>

      <ChartCard
        title="Subjects across terms"
        description="How each subject has moved over time."
        empty={subjectChartData.length === 0 || subjectNames.length === 0}
        emptyTitle="No subject history"
        emptyDescription="Publish scores in more than one subject to compare trends."
      >
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={subjectChartData} margin={{ top: 12, right: 12, left: 0, bottom: 8 }}>
            <CartesianGrid strokeDasharray="3 3" stroke={CHART_GRID} vertical={false} />
            <XAxis
              dataKey="term_label"
              tick={{ fill: CHART_TICK, fontSize: 11 }}
              interval="preserveStartEnd"
            />
            <YAxis domain={[0, 100]} tick={{ fill: CHART_TICK, fontSize: 12 }} width={36} />
            <Tooltip formatter={(value) => formatScore(Number(value))} />
            <Legend />
            {subjectNames.map((name, index) => (
              <Line
                key={name}
                type="monotone"
                dataKey={name}
                stroke={CHART_SERIES[index % CHART_SERIES.length]}
                strokeWidth={2}
                dot={false}
                connectNulls
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>

      <div className="flex flex-wrap items-center gap-2">
        <FilterComponent
          filterName="Term"
          filterKey="performance-grade-term"
          options={terms.map((term) => ({ value: term.term_id, label: term.term_label }))}
          value={resolvedGradeTermId}
          allowEmpty={false}
          onChange={setGradeTermSelection}
          className="min-w-48"
        />
        {selectedGradeTerm ? (
          <p className="text-sm text-slate-500">{selectedGradeTerm.class_display_name}</p>
        ) : null}
      </div>

      {selectedGradeTerm ? (
        <GradePieChart
          title={gradeIsScoreBands ? 'Scores this term' : 'Grades this term'}
          mode={gradeMode}
          description={
            gradeIsScoreBands
              ? selectedGradeTerm.total_graded > 0
                ? `${selectedGradeTerm.total_graded} published scores for ${selectedGradeTerm.term_label}. This class uses positions — showing score ranges (pass mark ${formatScore(selectedGradeTerm.pass_mark)}%).`
                : `This class uses positions — score ranges will appear once results are published (pass mark ${formatScore(selectedGradeTerm.pass_mark)}%).`
              : `Subject grades for ${selectedGradeTerm.term_label}.`
          }
          rows={selectedGradeTerm.grade_distribution}
          totalGraded={selectedGradeTerm.total_graded}
          emptyTitle={gradeIsScoreBands ? 'No published scores yet' : 'No graded scores yet'}
          emptyDescription={
            gradeIsScoreBands
              ? 'Publish subject results for this term to see the score ranges.'
              : 'Publish graded subject results for this term to see the distribution.'
          }
        />
      ) : null}

      <ChartCard
        title="Subject ranking"
        description={
          isAllTimeRanking
            ? 'Subjects ranked by average score across terms with published results.'
            : rankingTerm
              ? `Subjects ranked from highest to lowest for ${rankingTerm.term_label}.`
              : 'Subjects ranked from highest to lowest.'
        }
        actions={
          <FilterComponent
            filterName="Period"
            filterKey="performance-ranking-period"
            options={rankingOptions}
            value={resolvedRankingKey}
            allowEmpty={false}
            onChange={setRankingSelection}
            className="min-w-48"
          />
        }
        empty={rankedSubjects.length === 0}
        emptyTitle="No subjects to rank"
        emptyDescription="Published subject scores will appear here, ranked from best to weakest."
        bodyClassName="w-full"
      >
        {isAllTimeRanking && data.all_time_incomplete ? (
          <p className="mb-3 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">
            Some subjects are missing scores in one or more terms. Ranking uses only the terms that
            have results so far.
          </p>
        ) : null}
        {!isAllTimeRanking && rankingTerm?.results_incomplete ? (
          <p className="mb-3 rounded-md bg-amber-50 px-3 py-2 text-sm text-amber-800">
            {rankingTerm.missing_subjects_count === 1
              ? '1 subject still has no published result this term. Ranking shows subjects that are in so far.'
              : `${rankingTerm.missing_subjects_count} subjects still have no published results this term. Ranking shows subjects that are in so far.`}
          </p>
        ) : null}
        <RankingList
          subjects={rankedSubjects}
          scoreCaption={isAllTimeRanking ? 'avg' : 'this term'}
        />
      </ChartCard>
    </div>
  )
}

export default Performance
