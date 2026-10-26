import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useAuthStore } from '@/features/auth/store'
import { getApiErrorMessage } from '@/utils'
import NeedsAttentionCard from '../components/NeedsAttentionCard'
import OverviewCard from '../components/OverviewCard'
import RecentActivitiesCard from '../components/RecentActivitiesCard'
import WelcomeBanner from '../components/WelcomeBanner'
import { getStaffDashboard } from '../services'
import type { OverviewMetric } from '../types'
import {
  formatDashboardCount,
  padDashboardCount,
  STAFF_DASHBOARD_QUERY_KEY,
} from '../utils'

const StaffDashboard = () => {
  const firstName = useAuthStore((state) => state.user?.first_name ?? '')

  const { data, isLoading, isError, error } = useQuery({
    queryKey: [STAFF_DASHBOARD_QUERY_KEY],
    queryFn: getStaffDashboard,
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
        label: 'Teachers',
        value: formatDashboardCount(overview?.teachers_count ?? 0),
      },
    ]
  }, [data?.school_overview])

  const academicMetrics = useMemo<OverviewMetric[]>(() => {
    const overview = data?.academic_overview
    return [
      {
        label: 'Pending Reports',
        value: padDashboardCount(overview?.pending_reports ?? 0),
      },
      {
        label: 'Reports Ready',
        value: formatDashboardCount(overview?.reports_ready ?? 0),
      },
      {
        label: 'Released',
        value: formatDashboardCount(overview?.released_reports ?? 0),
      },
    ]
  }, [data?.academic_overview])

  const coverageMetrics = useMemo<OverviewMetric[]>(() => {
    const overview = data?.coverage_overview
    return [
      {
        label: 'No Class Teacher',
        value: padDashboardCount(overview?.unassigned_classes ?? 0),
      },
      {
        label: 'No Subject Teacher',
        value: padDashboardCount(overview?.unassigned_subjects ?? 0),
      },
      {
        label: 'Empty Classes',
        value: padDashboardCount(overview?.empty_classes ?? 0),
      },
    ]
  }, [data?.coverage_overview])

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

  if (isError || !data) {
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
          <OverviewCard title="Academic Overview" metrics={academicMetrics} />
          <OverviewCard title="Class Coverage" metrics={coverageMetrics} />
        </div>
      </WelcomeBanner>

      <div className="mt-6 grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <NeedsAttentionCard items={data.needs_attention} />
        </div>
        <RecentActivitiesCard activities={data.activities} />
      </div>
    </div>
  )
}

export default StaffDashboard
