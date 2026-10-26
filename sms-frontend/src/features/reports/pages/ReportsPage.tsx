import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import ActionBar from '@/components/shared/ActionBar'
import { TabComponent } from '@/components/shared'
import FilterComponent, { type FilterSelection } from '@/components/ui/FilterComponent'
import { Capability } from '@/features/auth/capabilities'
import { useAccess, useCan } from '@/features/auth/hooks'
import { getApiErrorMessage } from '@/utils'
import AcademicTab from '../components/AcademicTab'
import EnrollmentTab from '../components/EnrollmentTab'
import FinanceTab from '../components/FinanceTab'
import OverviewTab from '../components/OverviewTab'
import StaffTab from '../components/StaffTab'
import TeacherDeskTab from '../components/TeacherDeskTab'
import {
  getReportsByClass,
  getReportsEnrollment,
  getReportsFeesAcademicRisk,
  getReportsFilterOptions,
  getReportsFinance,
  getReportsGradeDistribution,
  getReportsOverview,
  getReportsStaffCapacity,
  getReportsStudentTrends,
  getReportsSubjectHeatmap,
  getReportsTeacherDesk,
  getReportsWorkflow,
} from '../services'
import {
  REPORTS_BY_CLASS_QUERY_KEY,
  REPORTS_ENROLLMENT_QUERY_KEY,
  REPORTS_FEES_RISK_QUERY_KEY,
  REPORTS_FILTERS_QUERY_KEY,
  REPORTS_FINANCE_QUERY_KEY,
  REPORTS_GRADE_DIST_QUERY_KEY,
  REPORTS_HEATMAP_QUERY_KEY,
  REPORTS_OVERVIEW_QUERY_KEY,
  REPORTS_STAFF_QUERY_KEY,
  REPORTS_STUDENT_TRENDS_QUERY_KEY,
  REPORTS_TEACHER_DESK_QUERY_KEY,
  REPORTS_WORKFLOW_QUERY_KEY,
} from '../utils'

const TAB_OVERVIEW = 'Overview'
const TAB_MY_CLASSES = 'My classes'
const TAB_MY_SUBJECTS = 'My subjects'
const TAB_FINANCE = 'Finance'
const TAB_ACADEMIC = 'Academic'
const TAB_ENROLLMENT = 'Enrollment'
const TAB_TEACHERS = 'Teachers'

const TAB_FROM_QUERY: Record<string, string> = {
  overview: TAB_OVERVIEW,
  finance: TAB_FINANCE,
  academic: TAB_ACADEMIC,
  enrollment: TAB_ENROLLMENT,
  teachers: TAB_TEACHERS,
  'my-classes': TAB_MY_CLASSES,
  'my-subjects': TAB_MY_SUBJECTS,
}

const QUERY_FROM_TAB: Record<string, string> = {
  [TAB_OVERVIEW]: 'overview',
  [TAB_FINANCE]: 'finance',
  [TAB_ACADEMIC]: 'academic',
  [TAB_ENROLLMENT]: 'enrollment',
  [TAB_TEACHERS]: 'teachers',
  [TAB_MY_CLASSES]: 'my-classes',
  [TAB_MY_SUBJECTS]: 'my-subjects',
}

const ReportsPage = () => {
  const [searchParams, setSearchParams] = useSearchParams()
  const access = useAccess()
  const isTeacherScoped = access.mode === 'scoped'
  const showMyClasses = isTeacherScoped && access.is_class_teacher
  const showMySubjects = isTeacherScoped && access.is_subject_teacher
  const showFinance = useCan(Capability.NAV_FEES)
  const showAcademic = useCan(Capability.NAV_ASSESSMENTS)
  const canCreateStudents = useCan(Capability.STUDENTS_CREATE)
  const showTeachers = useCan(Capability.NAV_STAFF)
  const showEnrollment = canCreateStudents || showTeachers

  const defaultTeacherTab = showMyClasses
    ? TAB_MY_CLASSES
    : showMySubjects
      ? TAB_MY_SUBJECTS
      : TAB_ACADEMIC

  const defaultSchoolTab = showFinance && !showAcademic ? TAB_FINANCE : TAB_OVERVIEW

  const [termId, setTermId] = useState<FilterSelection>('')
  const [compareTermId, setCompareTermId] = useState<FilterSelection>('')

  const [workflowLevelId, setWorkflowLevelId] = useState<FilterSelection>('')
  const [classChartLevelId, setClassChartLevelId] = useState<FilterSelection>('')
  const [heatmapLevelId, setHeatmapLevelId] = useState<FilterSelection>('')
  const [heatmapClassLevelId, setHeatmapClassLevelId] = useState<FilterSelection>('')
  const [gradeClassLevelId, setGradeClassLevelId] = useState<FilterSelection>('')
  const [studentsClassLevelId, setStudentsClassLevelId] = useState<FilterSelection>('')

  const teacherTabs = useMemo(() => {
    const tabs = new Set<string>([TAB_ACADEMIC])
    if (showMyClasses) tabs.add(TAB_MY_CLASSES)
    if (showMySubjects) tabs.add(TAB_MY_SUBJECTS)
    return tabs
  }, [showMyClasses, showMySubjects])

  const schoolTabs = useMemo(() => {
    const tabs = new Set<string>()
    // Accountant: finance only. Staff/admin: overview + role-relevant tabs.
    if (!(showFinance && !showAcademic)) {
      tabs.add(TAB_OVERVIEW)
    }
    if (showFinance) tabs.add(TAB_FINANCE)
    if (showAcademic) tabs.add(TAB_ACADEMIC)
    if (showEnrollment) tabs.add(TAB_ENROLLMENT)
    if (showTeachers) tabs.add(TAB_TEACHERS)
    return tabs
  }, [showFinance, showAcademic, showEnrollment, showTeachers])

  const tabFromParam = searchParams.get('tab')
  const selectedTab =
    tabFromParam && TAB_FROM_QUERY[tabFromParam.toLowerCase()]
      ? TAB_FROM_QUERY[tabFromParam.toLowerCase()]
      : null

  const activeTab = isTeacherScoped
    ? selectedTab && teacherTabs.has(selectedTab)
      ? selectedTab
      : defaultTeacherTab
    : selectedTab && schoolTabs.has(selectedTab)
      ? selectedTab
      : defaultSchoolTab

  const selectTab = (label: string) => {
    const key = QUERY_FROM_TAB[label]
    if (!key) return
    const next = new URLSearchParams(searchParams)
    next.set('tab', key)
    setSearchParams(next, { replace: true })
  }

  const { data: filterOptions, isLoading: filtersLoading } = useQuery({
    queryKey: [REPORTS_FILTERS_QUERY_KEY],
    queryFn: getReportsFilterOptions,
  })

  const levels = filterOptions?.levels ?? []
  const classLevels = filterOptions?.class_levels ?? []
  const defaultLevelId = levels[0]?.id ?? ''
  const defaultClassLevelId = classLevels[0]?.id ?? ''

  const resolvedTermId =
    termId !== '' ? String(termId) : (filterOptions?.active_term_id ?? '')
  const resolvedHeatmapLevelId =
    heatmapLevelId !== '' ? String(heatmapLevelId) : defaultLevelId
  const resolvedGradeClassLevelId =
    gradeClassLevelId !== '' ? String(gradeClassLevelId) : defaultClassLevelId

  const globalParams = useMemo(
    () => ({
      term_id: resolvedTermId || undefined,
      compare_term_id: compareTermId === '' ? undefined : String(compareTermId),
    }),
    [resolvedTermId, compareTermId],
  )

  const termReady = Boolean(resolvedTermId)
  const teacherDeskTab =
    activeTab === TAB_MY_CLASSES || activeTab === TAB_MY_SUBJECTS

  const {
    data: overview,
    isLoading: overviewLoading,
    isError: overviewError,
    error: overviewErr,
  } = useQuery({
    queryKey: [REPORTS_OVERVIEW_QUERY_KEY, globalParams],
    queryFn: () => getReportsOverview(globalParams),
    enabled: termReady && (!isTeacherScoped || activeTab === TAB_ACADEMIC),
  })

  const { data: workflow } = useQuery({
    queryKey: [REPORTS_WORKFLOW_QUERY_KEY, resolvedTermId, workflowLevelId],
    queryFn: () =>
      getReportsWorkflow({
        term_id: resolvedTermId,
        level_id: workflowLevelId === '' ? undefined : String(workflowLevelId),
      }),
    enabled: termReady && activeTab === TAB_OVERVIEW && !isTeacherScoped,
  })

  const { data: feesRisk } = useQuery({
    queryKey: [REPORTS_FEES_RISK_QUERY_KEY, resolvedTermId],
    queryFn: () => getReportsFeesAcademicRisk({ term_id: resolvedTermId, limit: 8 }),
    enabled:
      termReady &&
      activeTab === TAB_OVERVIEW &&
      !isTeacherScoped &&
      overview?.scope_mode === 'school',
  })

  const { data: teacherDesk } = useQuery({
    queryKey: [REPORTS_TEACHER_DESK_QUERY_KEY, resolvedTermId],
    queryFn: () => getReportsTeacherDesk({ term_id: resolvedTermId }),
    enabled: termReady && isTeacherScoped && teacherDeskTab,
  })

  const { data: finance } = useQuery({
    queryKey: [REPORTS_FINANCE_QUERY_KEY, resolvedTermId],
    queryFn: () => getReportsFinance({ term_id: resolvedTermId, limit: 10 }),
    enabled: termReady && !isTeacherScoped && activeTab === TAB_FINANCE,
  })

  const { data: byClass } = useQuery({
    queryKey: [REPORTS_BY_CLASS_QUERY_KEY, resolvedTermId, classChartLevelId],
    queryFn: () =>
      getReportsByClass({
        term_id: resolvedTermId,
        level_id: classChartLevelId === '' ? undefined : String(classChartLevelId),
      }),
    enabled: termReady && activeTab === TAB_ACADEMIC,
  })

  const { data: heatmap } = useQuery({
    queryKey: [
      REPORTS_HEATMAP_QUERY_KEY,
      resolvedTermId,
      resolvedHeatmapLevelId,
      heatmapClassLevelId,
    ],
    queryFn: () =>
      getReportsSubjectHeatmap({
        term_id: resolvedTermId,
        level_id: resolvedHeatmapLevelId,
        class_level_id:
          heatmapClassLevelId === '' ? undefined : String(heatmapClassLevelId),
      }),
    enabled: termReady && activeTab === TAB_ACADEMIC && Boolean(resolvedHeatmapLevelId),
  })

  const { data: gradeDist } = useQuery({
    queryKey: [REPORTS_GRADE_DIST_QUERY_KEY, resolvedTermId, resolvedGradeClassLevelId],
    queryFn: () =>
      getReportsGradeDistribution({
        term_id: resolvedTermId,
        class_level_id: resolvedGradeClassLevelId,
      }),
    enabled: termReady && activeTab === TAB_ACADEMIC && Boolean(resolvedGradeClassLevelId),
  })

  const { data: trends } = useQuery({
    queryKey: [REPORTS_STUDENT_TRENDS_QUERY_KEY, resolvedTermId, studentsClassLevelId],
    queryFn: () =>
      getReportsStudentTrends({
        term_id: resolvedTermId,
        class_level_id: studentsClassLevelId === '' ? undefined : String(studentsClassLevelId),
        limit: 8,
      }),
    enabled: termReady && activeTab === TAB_ACADEMIC,
  })

  const { data: enrollment } = useQuery({
    queryKey: [REPORTS_ENROLLMENT_QUERY_KEY, resolvedTermId],
    queryFn: () => getReportsEnrollment({ term_id: resolvedTermId }),
    enabled: termReady && !isTeacherScoped && activeTab === TAB_ENROLLMENT,
  })

  const { data: teachers } = useQuery({
    queryKey: [REPORTS_STAFF_QUERY_KEY, resolvedTermId],
    queryFn: () => getReportsStaffCapacity({ term_id: resolvedTermId }),
    enabled: termReady && !isTeacherScoped && activeTab === TAB_TEACHERS,
  })

  const termOptions = useMemo(
    () =>
      (filterOptions?.terms ?? []).map((term) => ({
        value: term.id,
        label: term.is_active ? `${term.label} (active)` : term.label,
      })),
    [filterOptions?.terms],
  )

  const compareOptions = useMemo(
    () => termOptions.filter((option) => option.value !== resolvedTermId),
    [termOptions, resolvedTermId],
  )

  const tabs = isTeacherScoped
    ? [
        ...(showMyClasses
          ? [
              {
                label: TAB_MY_CLASSES,
                icon: 'hugeicons:teaching',
                onClick: () => selectTab(TAB_MY_CLASSES),
              },
            ]
          : []),
        ...(showMySubjects
          ? [
              {
                label: TAB_MY_SUBJECTS,
                icon: 'hugeicons:book-open-01',
                onClick: () => selectTab(TAB_MY_SUBJECTS),
              },
            ]
          : []),
        {
          label: TAB_ACADEMIC,
          icon: 'hugeicons:chart-average',
          onClick: () => selectTab(TAB_ACADEMIC),
        },
      ]
    : [
        ...(schoolTabs.has(TAB_OVERVIEW)
          ? [
              {
                label: TAB_OVERVIEW,
                icon: 'hugeicons:dashboard-square-02',
                onClick: () => selectTab(TAB_OVERVIEW),
              },
            ]
          : []),
        ...(showFinance
          ? [
              {
                label: TAB_FINANCE,
                icon: 'hugeicons:money-bag-02',
                onClick: () => selectTab(TAB_FINANCE),
              },
            ]
          : []),
        ...(showAcademic
          ? [
              {
                label: TAB_ACADEMIC,
                icon: 'hugeicons:chart-average',
                onClick: () => selectTab(TAB_ACADEMIC),
              },
            ]
          : []),
        ...(showEnrollment
          ? [
              {
                label: TAB_ENROLLMENT,
                icon: 'hugeicons:student',
                onClick: () => selectTab(TAB_ENROLLMENT),
              },
            ]
          : []),
        ...(showTeachers
          ? [
              {
                label: TAB_TEACHERS,
                icon: 'hugeicons:teaching',
                onClick: () => selectTab(TAB_TEACHERS),
              },
            ]
          : []),
      ]

  return (
    <div className="space-y-6">
      <ActionBar title="Reports & Insights">
        <FilterComponent
          filterName="Term"
          filterKey="reports-term"
          options={termOptions}
          value={resolvedTermId}
          placeholder={filtersLoading ? 'Loading…' : 'Select term'}
          onChange={(value) => {
            setTermId(value)
            if (value !== '' && value === compareTermId) setCompareTermId('')
          }}
        />
        {!isTeacherScoped || activeTab === TAB_ACADEMIC ? (
          <FilterComponent
            filterName="Compare"
            filterKey="reports-compare"
            options={compareOptions}
            value={compareTermId}
            placeholder="No comparison"
            onChange={setCompareTermId}
            disabled={compareOptions.length === 0}
          />
        ) : null}
      </ActionBar>

      <TabComponent activeTab={activeTab} tabs={tabs} />

      {overviewError && activeTab === TAB_ACADEMIC ? (
        <div className="bg-white p-6 custom-shadow-md">
          <p className="text-sm text-rose-600">
            {getApiErrorMessage(overviewErr, 'Could not load reports.')}
          </p>
        </div>
      ) : null}

      {!isTeacherScoped && overviewLoading && !overview && activeTab === TAB_OVERVIEW ? (
        <div className="bg-white p-8 custom-shadow-md text-sm text-slate-500">
          Loading insights…
        </div>
      ) : null}

      {!isTeacherScoped && overview && activeTab === TAB_OVERVIEW ? (
        <OverviewTab
          overview={overview}
          workflow={workflow}
          feesRisk={feesRisk}
          levels={levels}
          workflowLevelId={workflowLevelId}
          onWorkflowLevelChange={setWorkflowLevelId}
          showSchoolPanels
          showFeesRisk={showFinance}
        />
      ) : null}

      {isTeacherScoped && activeTab === TAB_MY_CLASSES ? (
        <TeacherDeskTab data={teacherDesk} mode="classes" />
      ) : null}

      {isTeacherScoped && activeTab === TAB_MY_SUBJECTS ? (
        <TeacherDeskTab data={teacherDesk} mode="subjects" />
      ) : null}

      {!isTeacherScoped && activeTab === TAB_FINANCE ? <FinanceTab data={finance} /> : null}

      {activeTab === TAB_ACADEMIC ? (
        overviewLoading && !overview ? (
          <div className="bg-white p-8 custom-shadow-md text-sm text-slate-500">
            Loading academic insights…
          </div>
        ) : overview ? (
          <AcademicTab
            overview={overview}
            byClass={byClass}
            heatmap={heatmap}
            gradeDist={gradeDist}
            trends={trends}
            levels={levels}
            classLevels={classLevels}
            classLevelFilter={classChartLevelId}
            gradeClassFilter={resolvedGradeClassLevelId}
            heatmapLevelFilter={resolvedHeatmapLevelId}
            heatmapClassFilter={heatmapClassLevelId}
            studentsClassFilter={studentsClassLevelId}
            onClassLevelFilter={setClassChartLevelId}
            onGradeClassFilter={setGradeClassLevelId}
            onHeatmapLevelFilter={setHeatmapLevelId}
            onHeatmapClassFilter={setHeatmapClassLevelId}
            onStudentsClassFilter={setStudentsClassLevelId}
          />
        ) : null
      ) : null}

      {!isTeacherScoped && activeTab === TAB_ENROLLMENT ? (
        <EnrollmentTab data={enrollment} />
      ) : null}

      {!isTeacherScoped && activeTab === TAB_TEACHERS ? (
        <StaffTab data={teachers} />
      ) : null}
    </div>
  )
}

export default ReportsPage
