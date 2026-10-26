import { Link } from 'react-router-dom'
import { Button } from '@/components/ui'
import { useAuthStore } from '@/features/auth/store'
import WelcomeBanner from '../components/WelcomeBanner'
import OverviewCard from '../components/OverviewCard'
import type { OverviewMetric } from '../types'

const StaffDashboard = () => {
  const firstName = useAuthStore((state) => state.user?.first_name ?? '')

  const shortcuts: OverviewMetric[] = [
    { label: 'Students', value: 'Enroll & update' },
    { label: 'Assessments', value: 'Release results' },
    { label: 'Staff', value: 'Manage teachers' },
  ]

  return (
    <div>
      <WelcomeBanner firstName={firstName}>
        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          <OverviewCard title="Your workspace" metrics={shortcuts} />
        </div>
      </WelcomeBanner>

      <div className="mt-4 flex flex-wrap gap-3">
        <Link to="/students">
          <Button type="button">Students</Button>
        </Link>
        <Link to="/assessments">
          <Button type="button" variant="outline">
            Assessments
          </Button>
        </Link>
        <Link to="/staff">
          <Button type="button" variant="outline">
            Staff directory
          </Button>
        </Link>
        <Link to="/reports">
          <Button type="button" variant="outline">
            Insights
          </Button>
        </Link>
      </div>

      <div className="mt-6 rounded-xl bg-white p-6 custom-shadow-md">
        <h2 className="text-base font-medium text-slate-900">What you can do</h2>
        <ul className="mt-3 space-y-2 text-sm text-slate-600 list-disc pl-5">
          <li>Add and update student records, including marking leavers.</li>
          <li>Help with assessments — approve and release results.</li>
          <li>Manage teachers in the staff directory.</li>
          <li>View classes and enrollment insights (fees stay with the accountant).</li>
        </ul>
      </div>
    </div>
  )
}

export default StaffDashboard
