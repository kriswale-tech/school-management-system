import FilterComponent, { type FilterSelection } from '@/components/ui/FilterComponent'
import ChartCard from './ChartCard'
import type { ClassLevelOption, LevelOption, SubjectHeatmapResponse } from '../types'
import { formatScore, heatColor } from '../utils'

type SubjectHeatmapProps = {
  data?: SubjectHeatmapResponse
  levels: LevelOption[]
  classLevels: ClassLevelOption[]
  levelId: FilterSelection
  classLevelId: FilterSelection
  onLevelChange: (value: FilterSelection) => void
  onClassLevelChange: (value: FilterSelection) => void
}

const SubjectHeatmap = ({
  data,
  levels,
  classLevels,
  levelId,
  classLevelId,
  onLevelChange,
  onClassLevelChange,
}: SubjectHeatmapProps) => {
  const classes = data?.classes ?? []
  const subjects = data?.subjects ?? []
  const sizeByClass = new Map(
    (data?.class_sizes ?? []).map((row) => [row.display_name, row.students_count]),
  )
  const cellMap = new Map(
    (data?.cells ?? []).map((cell) => [
      `${cell.class_display_name}::${cell.subject_name}`,
      cell,
    ]),
  )

  const levelClasses = classLevels.filter((item) => item.level_id === String(levelId))
  const empty = !levelId || subjects.length === 0
  const hasScores = (data?.cells ?? []).some((cell) => cell.score_count > 0)
  const studentsLabel =
    data?.students_count !== undefined
      ? `${data.students_count} student${data.students_count === 1 ? '' : 's'} in view`
      : null

  return (
    <ChartCard
      title="Subject heat map"
      description={
        data?.level_name
          ? [
              `Average published scores for ${data.level_name} only (same subject catalog).`,
              studentsLabel,
            ]
              .filter(Boolean)
              .join(' ')
          : 'Pick a level — subjects are compared within that level only.'
      }
      info="Grid of class × subject averages for one level. Cell colour is the average of published scores in that subject for that class (darker = higher). Levels are never mixed because curricula and grade systems differ."
      empty={empty}
      emptyTitle={levelId ? 'No subjects for this level' : 'Select a level'}
      emptyDescription={
        levelId
          ? 'Add subjects to this level, then publish scores to fill the grid.'
          : 'Heat maps stay within one level so classes share a subject set.'
      }
      bodyClassName="w-full overflow-x-auto"
      actions={
        <>
          {levels.length > 0 ? (
            <FilterComponent
              filterName="Level"
              filterKey="heatmap-level"
              options={levels.map((level) => ({ value: level.id, label: level.name }))}
              value={levelId}
              allowEmpty={false}
              onChange={(value) => {
                onLevelChange(value)
                onClassLevelChange('')
              }}
              className="min-w-36"
            />
          ) : null}
          {levelClasses.length > 0 ? (
            <FilterComponent
              filterName="Class"
              filterKey="heatmap-class"
              options={levelClasses.map((item) => ({ value: item.id, label: item.name }))}
              value={classLevelId}
              placeholder="All classes"
              onChange={onClassLevelChange}
              className="min-w-36"
            />
          ) : null}
        </>
      }
    >
      {!hasScores && subjects.length > 0 ? (
        <p className="mb-3 text-sm text-slate-500">
          Grid shows this level’s subjects. Cells fill as scores are published.
        </p>
      ) : null}
      <table className="min-w-full border-collapse text-sm">
        <thead>
          <tr>
            <th className="sticky left-0 z-10 bg-white px-3 py-2 text-left font-medium text-slate-500">
              Class
            </th>
            {subjects.map((subject) => (
              <th
                key={subject}
                className="px-2 py-2 text-center font-medium text-slate-500 whitespace-nowrap"
              >
                {subject}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {classes.map((className) => {
            const enrolled = sizeByClass.get(className) ?? 0
            return (
              <tr key={className} className="border-t border-slate-100">
                <th className="sticky left-0 z-10 bg-white px-3 py-2 text-left font-medium text-slate-700 whitespace-nowrap">
                  <span>{className}</span>
                  <span className="mt-0.5 block text-xs font-normal text-slate-500">
                    {enrolled} student{enrolled === 1 ? '' : 's'}
                  </span>
                </th>
                {subjects.map((subject) => {
                  const cell = cellMap.get(`${className}::${subject}`)
                  const average = cell?.average_score ?? null
                  const scoreCount = cell?.score_count ?? 0
                  return (
                    <td key={`${className}-${subject}`} className="px-1.5 py-1.5 text-center">
                      <div
                        className="mx-auto flex h-10 min-w-14 items-center justify-center rounded-sm text-xs font-medium text-slate-800"
                        style={{ backgroundColor: heatColor(average) }}
                        title={
                          average === null
                            ? `${enrolled} students · no published scores`
                            : `${formatScore(average)} · ${scoreCount} of ${enrolled} published`
                        }
                      >
                        {formatScore(average)}
                      </div>
                    </td>
                  )
                })}
              </tr>
            )
          })}
        </tbody>
      </table>
      <div className="mt-3 flex items-center gap-2 text-xs text-slate-500">
        <span>Low</span>
        <div
          className="h-2 w-28 rounded-sm"
          style={{
            background: `linear-gradient(90deg, ${heatColor(20)}, ${heatColor(90)})`,
          }}
        />
        <span>High</span>
      </div>
    </ChartCard>
  )
}

export default SubjectHeatmap
