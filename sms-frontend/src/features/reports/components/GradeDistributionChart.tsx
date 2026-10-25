import FilterComponent, { type FilterSelection } from '@/components/ui/FilterComponent'
import GradePieChart from './GradePieChart'
import type { ClassLevelOption, GradeDistributionResponse } from '../types'
import { formatResultsCoverage, formatScore } from '../utils'

type GradeDistributionChartProps = {
  data?: GradeDistributionResponse
  classLevels: ClassLevelOption[]
  classLevelId: FilterSelection
  onClassLevelChange: (value: FilterSelection) => void
}

const GradeDistributionChart = ({
  data,
  classLevels,
  classLevelId,
  onClassLevelChange,
}: GradeDistributionChartProps) => {
  const mode = data?.mode ?? 'grades'
  const isScoreBands = mode === 'score_bands'
  const totalGraded = data?.total_graded ?? 0
  const rows = data?.results ?? []
  const hasClass = Boolean(classLevelId)
  const coverage =
    hasClass && data
      ? formatResultsCoverage(data.students_with_results, data.students_count)
      : null
  const classLabel = data?.class_level_name ?? 'this class'

  const description = !hasClass
    ? 'Pick a class to see how published scores are spread.'
    : isScoreBands
      ? totalGraded > 0
        ? `${coverage} in ${classLabel} · ${totalGraded} published scores. This class uses positions — showing score ranges (pass mark ${formatScore(data?.pass_mark)}%).`
        : `${coverage} in ${classLabel}. Score ranges will appear once results are published (pass mark ${formatScore(data?.pass_mark)}%).`
      : totalGraded > 0
        ? `${coverage} in ${classLabel} · ${totalGraded} graded published scores.`
        : `${coverage} in ${classLabel}. Letter or number grades appear once subject scores are published.`

  return (
    <GradePieChart
      title={isScoreBands ? 'Score distribution' : 'Grade distribution'}
      description={description}
      info={
        isScoreBands
          ? 'This class is set to positions only, so slices are score ranges instead of letter grades. Ranges are built around the pass mark from Assessment Settings.'
          : 'Counts how many published subject scores fall in each grade band for the selected class, using that class level’s grade system.'
      }
      mode={mode}
      rows={rows}
      totalGraded={totalGraded}
      emptyTitle={hasClass ? (isScoreBands ? 'No published scores yet' : 'No graded scores yet') : 'Select a class'}
      emptyDescription={
        hasClass
          ? isScoreBands
            ? 'Publish subject results for this class to see the score-range pie.'
            : 'Publish subject results with grades for this class to see the distribution.'
          : 'Choose a class to view its grade or score-range distribution.'
      }
      actions={
        classLevels.length > 0 ? (
          <FilterComponent
            filterName="Class"
            filterKey="grade-class"
            options={classLevels.map((item) => ({ value: item.id, label: item.name }))}
            value={classLevelId}
            allowEmpty={false}
            onChange={onClassLevelChange}
            className="min-w-32"
          />
        ) : null
      }
    />
  )
}

export default GradeDistributionChart
