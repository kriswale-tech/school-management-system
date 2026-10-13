import { lazy, Suspense } from 'react'
import { Navigate, useNavigate, useParams } from 'react-router-dom'
import ActionBar from '@/components/shared/ActionBar'
import { TabComponent } from '@/components/shared'
import LoadingSpinner from '@/components/ui/LoadingSpinner'
import AcademicYearSection from '../components/AcademicYearSection'
import AlertsSection from '../components/AlertsSection'
import ProfileSection from '../components/ProfileSection'

const FeeSettings = lazy(() => import('@/features/fees/pages/FeeSettings'))
const AssessmentSettings = lazy(() => import('@/features/assessments/AssessmentSettings'))
const ManageClasses = lazy(() => import('@/features/classes/manage-classes/ManageClasses'))

const TABS = [
  { label: 'School profile', slug: 'school-profile' },
  { label: 'Academic year', slug: 'academic-year' },
  { label: 'Alerts', slug: 'alerts' },
  { label: 'Fees', slug: 'fees' },
  { label: 'Assessments', slug: 'assessments' },
  { label: 'Classes', slug: 'classes' },
] as const

type SettingsTabSlug = (typeof TABS)[number]['slug']

const isSettingsTab = (value: string | undefined): value is SettingsTabSlug =>
  TABS.some((tab) => tab.slug === value)

const SettingsPage = () => {
  const { tab } = useParams<{ tab: string }>()
  const navigate = useNavigate()

  if (!isSettingsTab(tab)) {
    return <Navigate to="/settings/school-profile" replace />
  }

  const activeTab = TABS.find((item) => item.slug === tab) ?? TABS[0]

  return (
    <div className="space-y-6">
      <ActionBar title="Settings" />

      <div className="bg-white p-4 custom-shadow-md">
        <TabComponent
          tabs={TABS.map((item) => ({
            label: item.label,
            onClick: () => navigate(`/settings/${item.slug}`),
          }))}
          activeTab={activeTab.label}
        />

        <div className="mt-6">
          {tab === 'school-profile' ? <ProfileSection /> : null}
          {tab === 'academic-year' ? <AcademicYearSection /> : null}
          {tab === 'alerts' ? <AlertsSection /> : null}
          {tab === 'fees' || tab === 'assessments' || tab === 'classes' ? (
            <Suspense fallback={<LoadingSpinner className="mx-auto" />}>
              {tab === 'fees' ? <FeeSettings embedded /> : null}
              {tab === 'assessments' ? <AssessmentSettings embedded /> : null}
              {tab === 'classes' ? <ManageClasses embedded /> : null}
            </Suspense>
          ) : null}
        </div>
      </div>
    </div>
  )
}

export default SettingsPage
