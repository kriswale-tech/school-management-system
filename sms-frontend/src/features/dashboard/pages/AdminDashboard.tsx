import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useAuthStore } from '@/features/auth/store'
import { getApiErrorMessage } from '@/utils'
import AcademicProgressCard from '../components/AcademicProgressCard'
import NeedsAttentionCard from '../components/NeedsAttentionCard'
import OverviewCard from '../components/OverviewCard'
import SetupHealthCard, { isSetupHealthIncomplete } from '../components/SetupHealthCard'
import TopDebtorsCard from '../components/TopDebtorsCard'
import WelcomeBanner from '../components/WelcomeBanner'
import { getAdminDashboard } from '../services'
import type { OverviewMetric } from '../types'
import {
  ADMIN_DASHBOARD_QUERY_KEY,
  formatCompactFeeAmount,
  formatDashboardCount,
  padDashboardCount,
} from '../utils'

const AdminDashboard = () => {
  const firstName = useAuthStore((state) => state.user?.first_name ?? '')

  const { data, isLoading, isError, error } = useQuery({
    queryKey: [ADMIN_DASHBOARD_QUERY_KEY],
    queryFn: getAdminDashboard,
  })

  const schoolMetrics = useMemo<OverviewMetric[]>(() => {
    const overview = data?.school_overview
    return [
      {
        label: 'Total Students',
        value: formatDashboardCount(overview?.total_students ?? 0),
      },
      {
        label: 'Classes',
        value: padDashboardCount(overview?.total_classes ?? 0),
      },
      {
        label: 'Staff Members',
        value: formatDashboardCount(overview?.staff_members ?? 0),
      },
    ]
  }, [data?.school_overview])

  const feesMetrics = useMemo<OverviewMetric[]>(() => {
    const overview = data?.fees_overview
    return [
      {
        label: 'Fees Collected',
        value: formatCompactFeeAmount(overview?.fees_collected ?? 0),
      },
      {
        label: 'Out. Balance',
        value: formatCompactFeeAmount(overview?.outstanding_balance ?? 0),
      },
      {
        label: 'Debtors',
        value: formatDashboardCount(overview?.debtors_count ?? 0),
      },
    ]
  }, [data?.fees_overview])

  const thirdCard = useMemo(() => {
    if (data?.show_academic_widgets) {
      const overview = data.academic_overview
      return {
        title: 'Academic Overview',
        metrics: [
          {
            label: 'Pending Reports',
            value: padDashboardCount(overview.pending_reports),
          },
          {
            label: 'Reports Ready',
            value: formatDashboardCount(overview.reports_ready),
          },
          {
            label: 'Released Reports',
            value: formatDashboardCount(overview.released_reports),
          },
        ] satisfies OverviewMetric[],
      }
    }

    const coverage = data?.coverage_overview
    return {
      title: 'Class Coverage',
      metrics: [
        {
          label: 'No Class Teacher',
          value: padDashboardCount(coverage?.unassigned_classes ?? 0),
        },
        {
          label: 'No Subject Teacher',
          value: padDashboardCount(coverage?.unassigned_subjects ?? 0),
        },
        {
          label: 'Empty Classes',
          value: padDashboardCount(coverage?.empty_classes ?? 0),
        },
      ] satisfies OverviewMetric[],
    }
  }, [data])

  if (isLoading) {
    return (
      <div className="animate-pulse">
        <div className="-mx-6 -mt-6 h-44 bg-slate-200" />
        <div className="relative z-10 -mt-12 grid gap-3 px-6 sm:-mt-14 sm:grid-cols-2 xl:grid-cols-3">
          <div className="h-28 bg-slate-200" />
          <div className="h-28 bg-slate-200" />
          <div className="h-28 bg-slate-200" />
        </div>
        <div className="mt-6 grid gap-4 lg:grid-cols-3">
          <div className="h-56 bg-slate-200 lg:col-span-2" />
          <div className="h-56 bg-slate-200" />
        </div>
      </div>
    )
  }

  if (isError) {
    return (
      <div className="bg-white p-6 custom-shadow-md">
        <p className="text-sm text-rose-600">
          {getApiErrorMessage(error, 'Could not load the dashboard.')}
        </p>
      </div>
    )
  }

  return (
    <div>
      <WelcomeBanner firstName={firstName}>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          <OverviewCard title="School Overview" metrics={schoolMetrics} />
          <OverviewCard title="Fees Overview" metrics={feesMetrics} />
          <OverviewCard title={thirdCard.title} metrics={thirdCard.metrics} />
        </div>
      </WelcomeBanner>

      <div className="mt-6 grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-4">
          <NeedsAttentionCard items={data?.needs_attention ?? []} />
          {data?.show_academic_widgets ? (
            <AcademicProgressCard progress={data.academic_progress} levels={data.levels} />
          ) : null}
          {data?.setup_health && isSetupHealthIncomplete(data.setup_health) ? (
            <SetupHealthCard health={data.setup_health} />
          ) : null}
        </div>
        <div>
          <TopDebtorsCard debtors={data?.top_debtors ?? []} />
        </div>
      </div>
    </div>
  )
}

export default AdminDashboard
