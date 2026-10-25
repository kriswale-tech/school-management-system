import type { FilterSelection } from '@/components/ui/FilterComponent'
import StatsCard from '@/components/shared/StatsCard'
import ClassAverageChart from './ClassAverageChart'
import GradeDistributionChart from './GradeDistributionChart'
import StudentTrendsPanel from './StudentTrendsPanel'
import SubjectHeatmap from './SubjectHeatmap'
import type {
  ByClassResponse,
  ClassLevelOption,
  GradeDistributionResponse,
  LevelOption,
  ReportsOverview,
  StudentTrendsResponse,
  SubjectHeatmapResponse,
} from '../types'

type AcademicTabProps = {
  overview?: ReportsOverview
  byClass?: ByClassResponse
  heatmap?: SubjectHeatmapResponse
  gradeDist?: GradeDistributionResponse
  trends?: StudentTrendsResponse
  levels: LevelOption[]
  classLevels: ClassLevelOption[]
  classLevelFilter: FilterSelection
  gradeClassFilter: FilterSelection
  heatmapLevelFilter: FilterSelection
  heatmapClassFilter: FilterSelection
  studentsClassFilter: FilterSelection
  onClassLevelFilter: (value: FilterSelection) => void
  onGradeClassFilter: (value: FilterSelection) => void
  onHeatmapLevelFilter: (value: FilterSelection) => void
  onHeatmapClassFilter: (value: FilterSelection) => void
  onStudentsClassFilter: (value: FilterSelection) => void
}

const AcademicTab = ({
  overview,
  byClass,
  heatmap,
  gradeDist,
  trends,
  levels,
  classLevels,
  classLevelFilter,
  gradeClassFilter,
  heatmapLevelFilter,
  heatmapClassFilter,
  studentsClassFilter,
  onClassLevelFilter,
  onGradeClassFilter,
  onHeatmapLevelFilter,
  onHeatmapClassFilter,
  onStudentsClassFilter,
}: AcademicTabProps) => {
  return (
    <div className="space-y-4">
      {overview ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
          <StatsCard title="Classes" value={String(overview.classes_count)} />
          <StatsCard
            title="Distinct subjects"
            value={String(overview.distinct_subjects_count)}
            description="Unique subject names across the school"
          />
          <StatsCard
            title="Subject–class slots"
            value={String(overview.class_subjects_count)}
            description={
              overview.unassigned_class_subjects > 0
                ? `${overview.unassigned_class_subjects} still need a teacher`
                : 'Subject offerings on each class'
            }
          />
          <StatsCard
            title="Teaching assignments"
            value={String(overview.teaching_assignments_count)}
            description="Subject×class slots with a teacher this term"
          />
        </div>
      ) : null}

      <ClassAverageChart
        rows={byClass?.results ?? []}
        levels={levels}
        levelId={classLevelFilter}
        onLevelChange={onClassLevelFilter}
        studentsCount={byClass?.students_count}
        studentsWithResults={byClass?.students_with_results}
      />

      <SubjectHeatmap
        data={heatmap}
        levels={levels}
        classLevels={classLevels}
        levelId={heatmapLevelFilter}
        classLevelId={heatmapClassFilter}
        onLevelChange={onHeatmapLevelFilter}
        onClassLevelChange={onHeatmapClassFilter}
      />

      <GradeDistributionChart
        data={gradeDist}
        classLevels={classLevels}
        classLevelId={gradeClassFilter}
        onClassLevelChange={onGradeClassFilter}
      />

      <StudentTrendsPanel
        topStudents={trends?.top_students ?? []}
        atRiskStudents={trends?.at_risk_students ?? []}
        passMark={trends?.pass_mark}
        studentsCount={trends?.students_count}
        studentsWithResults={trends?.students_with_results}
        belowPassCount={trends?.below_pass_count}
        classLevels={classLevels}
        classLevelId={studentsClassFilter}
        onClassLevelChange={onStudentsClassFilter}
      />
    </div>
  )
}

export default AcademicTab
