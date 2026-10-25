import { Link } from 'react-router-dom'
import StatsCard from '@/components/shared/StatsCard'
import FeesRiskCard from './FeesRiskCard'
import WorkflowPanel from './WorkflowPanel'
import type {
  FeesAcademicRiskResponse,
  LevelOption,
  ReportsOverview,
  WorkflowResponse,
} from '../types'
import { formatDelta, formatPercent, formatResultsCoverage, formatScore } from '../utils'
import type { FilterSelection } from '@/components/ui/FilterComponent'

type OverviewTabProps = {
  overview: ReportsOverview
  workflow?: WorkflowResponse
  feesRisk?: FeesAcademicRiskResponse
  levels: LevelOption[]
  workflowLevelId: FilterSelection
  onWorkflowLevelChange: (value: FilterSelection) => void
  /** Hide school-wide workflow / fees panels (teacher scoped view). */
  showSchoolPanels?: boolean
}

const OverviewTab = ({
  overview,
  workflow,
  feesRisk,
  levels,
  workflowLevelId,
  onWorkflowLevelChange,
  showSchoolPanels = true,
}: OverviewTabProps) => {
  const avgDelta = formatDelta(overview.compare?.average_score_delta)
  const passDelta = formatDelta(overview.compare?.pass_rate_delta, ' pts')

  return (
    <div className="space-y-4">
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <StatsCard
          title={overview.scope_mode === 'scoped' ? 'Your average' : 'School average'}
          value={formatScore(overview.average_score)}
          description={
            avgDelta
              ? `${avgDelta} vs ${overview.compare?.term_label ?? 'compare term'}`
              : `Pass mark is set at ${formatScore(overview.pass_mark)}%`
          }
        />
        <StatsCard
          title="Pass rate"
          value={formatPercent(overview.pass_rate)}
          description={
            passDelta
              ? `${passDelta} vs compare term`
              : formatResultsCoverage(
                  overview.students_with_results,
                  overview.students_count,
                )
          }
        />
        {showSchoolPanels ? (
          <StatsCard
            title="Workflow complete"
            value={formatPercent(workflow?.percent_complete)}
            description={`${workflow?.total_students ?? 0} students · ${workflow?.ready_count ?? 0} ready · ${workflow?.released_count ?? 0} released`}
          />
        ) : (
          <StatsCard
            title="Students in view"
            value={String(overview.students_count)}
            description={formatResultsCoverage(
              overview.students_with_results,
              overview.students_count,
            )}
          />
        )}
        <StatsCard
          title="Published scores"
          value={String(overview.published_subject_scores)}
          description={formatResultsCoverage(
            overview.students_with_results,
            overview.students_count,
          )}
        />
      </div>

      {overview.published_subject_scores === 0 ? (
        <div className="bg-white p-6 custom-shadow-md">
          <p className="text-sm text-slate-600">
            No published subject results for this term yet. Open{' '}
            <Link to="/assessments" className="text-sky-700 hover:underline">
              Assessments
            </Link>{' '}
            to track publishing, or switch term above.
          </p>
        </div>
      ) : null}

      {showSchoolPanels ? (
        <>
          <WorkflowPanel
            data={workflow}
            levels={levels}
            levelId={workflowLevelId}
            onLevelChange={onWorkflowLevelChange}
          />
          <FeesRiskCard data={feesRisk} />
        </>
      ) : (
        <div className="bg-white p-4 custom-shadow-md text-sm text-slate-600">
          Open <span className="font-medium text-slate-800">My classes</span> for grade curves
          and subject trends for your assignments.
        </div>
      )}
    </div>
  )
}

export default OverviewTab
