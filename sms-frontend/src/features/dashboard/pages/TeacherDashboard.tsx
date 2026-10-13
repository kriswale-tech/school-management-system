import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useAuthStore } from '@/features/auth/store'
import { getApiErrorMessage } from '@/utils'
import NeedsAttentionCard from '../components/NeedsAttentionCard'
import OverviewCard from '../components/OverviewCard'
import RecentActivitiesCard from '../components/RecentActivitiesCard'
import TeacherClassesCard from '../components/TeacherClassesCard'
import TeacherSubjectsCard from '../components/TeacherSubjectsCard'
import WelcomeBanner from '../components/WelcomeBanner'
import { getTeacherDashboard } from '../services'
import type { OverviewMetric, TeacherDashboard as TeacherDashboardData } from '../types'
import {
  formatDashboardCount,
  padDashboardCount,
  TEACHER_DASHBOARD_QUERY_KEY,
} from '../utils'

const academicMetrics = (data: TeacherDashboardData): OverviewMetric[] => {
  const academic = data.academic_overview
  if (data.is_class_teacher && data.is_subject_teacher) {
    return [
      { label: 'Ready for You', value: formatDashboardCount(academic.awaiting_approval) },
      { label: 'To Publish', value: padDashboardCount(academic.subjects_to_publish) },
      { label: 'Corrections', value: formatDashboardCount(academic.corrections_count) },
    ]
  }
  if (data.is_subject_teacher) {
    return [
      { label: 'To Publish', value: padDashboardCount(academic.subjects_to_publish) },
      { label: 'Published', value: padDashboardCount(academic.subjects_published) },
      { label: 'Corrections', value: formatDashboardCount(academic.corrections_count) },
    ]
  }
  return [
    { label: 'With Subject Teachers', value: padDashboardCount(academic.pending_reports) },
    { label: 'Ready for You', value: formatDashboardCount(academic.awaiting_approval) },
    { label: 'Approved', value: formatDashboardCount(academic.approved_reports) },
  ]
}

const TeacherDashboard = () => {
  const firstName = useAuthStore((state) => state.user?.first_name ?? '')

  const { data, isLoading, isError, error } = useQuery({
    queryKey: [TEACHER_DASHBOARD_QUERY_KEY],
    queryFn: getTeacherDashboard,
  })

  const cards = useMemo(() => {
    const items: { title: string; metrics: OverviewMetric[] }[] = []
    if (!data) return items

    if (data.is_class_teacher) {
      items.push({
        title: 'My Classes',
        metrics: [
          {
            label: 'Classes',
            value: padDashboardCount(data.classes_overview.classes_count),
          },
          {
            label: 'Students',
            value: formatDashboardCount(data.classes_overview.students_count),
          },
        ],
      })
    }

    if (data.is_subject_teacher) {
      items.push({
        title: 'My Subjects',
        metrics: [
          {
            label: 'Subjects',
            value: padDashboardCount(data.subjects_overview.subjects_count),
          },
          {
            label: 'Students',
            value: formatDashboardCount(data.subjects_overview.students_count),
          },
        ],
      })
    }

    const showAcademicCard = data.is_subject_teacher || data.show_academic_widgets
    if (showAcademicCard) {
      items.push({
        title: 'Academic Overview',
        metrics: academicMetrics(data),
      })
    }

    return items
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

  if (isError || !data) {
    return (
      <div className="bg-white p-6 custom-shadow-md">
        <p className="text-sm text-rose-600">
          {getApiErrorMessage(error, 'Could not load the dashboard.')}
        </p>
      </div>
    )
  }

  const hasAssignments = data.is_class_teacher || data.is_subject_teacher

  return (
    <div>
      <WelcomeBanner firstName={firstName}>
        {cards.length > 0 ? (
          <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
            {cards.map((card) => (
              <OverviewCard key={card.title} title={card.title} metrics={card.metrics} />
            ))}
          </div>
        ) : (
          <div className="bg-white p-4 custom-shadow-md">
            <h3 className="text-xl font-semibold text-slate-800">Your assignments</h3>
            <p className="mt-2 text-sm text-slate-500">
              No classes or subjects are assigned to you this term.
            </p>
          </div>
        )}
      </WelcomeBanner>

      <div className="mt-6 grid gap-4 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-4">
          {data.is_class_teacher ? (
            <TeacherClassesCard
              classes={data.classes}
              showAcademic={data.show_academic_widgets}
            />
          ) : null}
          {data.is_subject_teacher ? <TeacherSubjectsCard subjects={data.subjects} /> : null}
          {!hasAssignments ? (
            <div className="bg-white p-4 custom-shadow-md">
              <p className="text-sm text-slate-500 py-6 text-center">
                When you are assigned a class or a subject, it will show up here.
              </p>
            </div>
          ) : null}
        </div>
        <div className="space-y-4">
          <NeedsAttentionCard items={data.needs_attention} />
          <RecentActivitiesCard activities={data.activities} />
        </div>
      </div>
    </div>
  )
}

export default TeacherDashboard
