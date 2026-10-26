import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Button } from '@/components/ui'
import { useAuthStore } from '@/features/auth/store'
import { getFeeDeskList, getFeeDeskStats } from '@/features/fees/services'
import {
  FEE_DESK_QUERY_KEY,
  FEE_DESK_STATS_QUERY_KEY,
  formatDebtorsStat,
  formatFeeAmount,
  getFeeDeskFullName,
} from '@/features/fees/utils'
import { getApiErrorMessage } from '@/utils'
import FeePrepNotice from '../components/FeePrepNotice'
import OverviewCard from '../components/OverviewCard'
import TopDebtorsCard from '../components/TopDebtorsCard'
import WelcomeBanner from '../components/WelcomeBanner'
import type { AdminDashboardTopDebtor, OverviewMetric } from '../types'
import { formatDashboardCount } from '../utils'

const AccountantDashboard = () => {
  const firstName = useAuthStore((state) => state.user?.first_name ?? '')

  const { data: stats, isLoading: statsLoading, isError, error } = useQuery({
    queryKey: [FEE_DESK_STATS_QUERY_KEY, 'dashboard'],
    queryFn: () => getFeeDeskStats({}),
  })

  const { data: debtorsPage } = useQuery({
    queryKey: [FEE_DESK_QUERY_KEY, 'dashboard-debtors'],
    queryFn: () => getFeeDeskList({ debtors: true, page: 1, page_size: 5 }),
  })

  const feesMetrics: OverviewMetric[] = [
    {
      label: 'Fees Collected',
      value: formatFeeAmount(stats?.total_collected ?? '0'),
    },
    {
      label: 'Outstanding',
      value: formatFeeAmount(stats?.outstanding ?? '0'),
    },
    {
      label: 'Debtors',
      value: formatDebtorsStat(stats?.debtors_count ?? 0, stats?.total_students ?? 0),
    },
  ]

  const topDebtors: AdminDashboardTopDebtor[] = (debtorsPage?.results ?? []).map((row) => ({
    student_id: row.id,
    student_code: row.student_id,
    full_name: getFeeDeskFullName(row),
    class_display: row.stream?.full_name || row.class_level.name,
    outstanding_amount: row.remaining_balance,
  }))

  if (statsLoading) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="-mx-6 -mt-6 h-44 bg-slate-200" />
        <div className="h-28 bg-slate-200" />
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
      <FeePrepNotice variant="modal" />
      <WelcomeBanner firstName={firstName}>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          <OverviewCard title="Fees Overview" metrics={feesMetrics} />
          <OverviewCard
            title="This term"
            metrics={[
              {
                label: 'Students',
                value: formatDashboardCount(stats?.total_students ?? 0),
              },
              {
                label: 'In credit',
                value: formatDashboardCount(stats?.students_in_credit ?? 0),
              },
            ]}
          />
        </div>
      </WelcomeBanner>

      <div className="mt-4 flex flex-wrap gap-3">
        <Link to="/fees">
          <Button type="button">Open fees desk</Button>
        </Link>
        <Link to="/fees/settings">
          <Button type="button" variant="outline">
            Fee settings
          </Button>
        </Link>
      </div>

      <div className="mt-6 max-w-xl">
        <TopDebtorsCard debtors={topDebtors} />
      </div>
    </div>
  )
}

export default AccountantDashboard
