import ActionBar from '@/components/shared/ActionBar'
import { TabComponent } from '@/components/shared'
import { ActionButton } from '@/components/ui'
import FilterComponent, { type FilterSelection } from '@/components/ui/FilterComponent'
import SearchComponent from '@/components/ui/SearchComponent'
import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import StatsCard from '@/components/shared/StatsCard'
import ClassTable from '../components/ClassTable'
import SubjectClassTable from '../components/SubjectClassTable'
import TeacherClassesWorkspace from '../components/TeacherClassesWorkspace'
import { getClassList, getClassStats, getSubjectClassList } from '../services'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Capability } from '@/features/auth/capabilities'
import { useAccess, useCan } from '@/features/auth/hooks'

const TAB_CLASSES = 'Classes'
const TAB_SUBJECTS = 'Subjects'

const CLASS_ATTENTION_OPTIONS = [
  { value: 'unassigned', label: 'No class teacher' },
  { value: 'empty', label: 'Empty classes' },
] as const

const SUBJECT_ATTENTION_OPTIONS = [
  { value: 'unassigned', label: 'No subject teacher' },
  { value: 'empty', label: 'No students' },
] as const

const tabFromParam = (value: string | null) => (value === 'subjects' ? TAB_SUBJECTS : TAB_CLASSES)

const attentionFromParam = (value: string | null): FilterSelection => {
  if (value === 'unassigned' || value === 'empty') return value
  return ''
}

const AdminClassesPage = () => {
  const [search, setSearch] = useState('')
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const canManageClasses = useCan(Capability.CLASSES_MANAGE)
  const activeTab = tabFromParam(searchParams.get('tab'))
  const attention = attentionFromParam(searchParams.get('attention'))
  const isClassesTab = activeTab === TAB_CLASSES

  const handleTabChange = (tab: typeof TAB_CLASSES | typeof TAB_SUBJECTS) => {
    const next = new URLSearchParams(searchParams)
    next.set('tab', tab === TAB_SUBJECTS ? 'subjects' : 'classes')
    next.delete('attention')
    setSearchParams(next, { replace: true })
  }

  const handleAttentionChange = (value: FilterSelection) => {
    const next = new URLSearchParams(searchParams)
    if (typeof value === 'string' && value !== '') next.set('attention', value)
    else next.delete('attention')
    setSearchParams(next, { replace: true })
  }

  const { data, isLoading } = useQuery({
    queryKey: ['classes', 'list', { search }],
    queryFn: () => getClassList({ search: search || undefined }),
    enabled: isClassesTab,
  })

  const { data: subjects, isLoading: subjectsLoading } = useQuery({
    queryKey: ['classes', 'subjects', { search }],
    queryFn: () => getSubjectClassList({ search: search || undefined }),
    enabled: !isClassesTab,
  })

  const { data: stats } = useQuery({
    queryKey: ['classes', 'stats'],
    queryFn: getClassStats,
  })

  const filteredClasses = useMemo(() => {
    const rows = data?.results ?? []
    if (attention === 'unassigned') return rows.filter((row) => !row.is_assigned)
    if (attention === 'empty') return rows.filter((row) => row.students_count === 0)
    return rows
  }, [data?.results, attention])

  const filteredSubjects = useMemo(() => {
    const rows = subjects?.results ?? []
    if (attention === 'unassigned') return rows.filter((row) => !row.teacher)
    if (attention === 'empty') return rows.filter((row) => row.students_count === 0)
    return rows
  }, [subjects?.results, attention])

  const attentionOptions = isClassesTab ? CLASS_ATTENTION_OPTIONS : SUBJECT_ATTENTION_OPTIONS

  return (
    <div className="space-y-6">
      <ActionBar title="Classes">
        <SearchComponent value={search} onChange={setSearch} />
        <FilterComponent
          filterName="Attention"
          filterKey="attention"
          options={[...attentionOptions]}
          value={attention}
          placeholder="All"
          onChange={handleAttentionChange}
        />
        {canManageClasses ? (
          <ActionButton
            icon="hugeicons:settings-02"
            label="Manage Classes"
            tooltipSide="bottom"
            onClick={() => navigate('/classes/manage')}
          />
        ) : null}
      </ActionBar>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsCard title="Total Classes" value={String(stats?.total_classes ?? 0)} />
        <StatsCard title="Total Subjects" value={String(stats?.total_class_subjects ?? 0)} />
        <StatsCard
          title="Unassigned Subjects"
          value={String(stats?.unassigned_class_subjects ?? 0)}
        />
        <StatsCard title="Unassigned Classes" value={String(stats?.unassigned_classes ?? 0)} />
      </div>

      <TabComponent
        activeTab={activeTab}
        tabs={[
          { label: TAB_CLASSES, onClick: () => handleTabChange(TAB_CLASSES) },
          { label: TAB_SUBJECTS, onClick: () => handleTabChange(TAB_SUBJECTS) },
        ]}
      />

      {isClassesTab ? (
        <ClassTable
          classes={filteredClasses}
          isLoading={isLoading}
          onViewClass={(classItem) => {
            navigate(`/classes/${classItem.id}`)
          }}
        />
      ) : (
        <SubjectClassTable subjects={filteredSubjects} isLoading={subjectsLoading} />
      )}
    </div>
  )
}

const Classes = () => {
  const access = useAccess()
  const isTeacherWorkspace = access.mode === 'scoped'

  if (isTeacherWorkspace) {
    return (
      <div className="space-y-6">
        <ActionBar title="Classes" />
        <div className="bg-white p-4 custom-shadow-md">
          <TeacherClassesWorkspace />
        </div>
      </div>
    )
  }

  return <AdminClassesPage />
}

export default Classes
