import { Icon } from '@iconify/react'
import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import ActionBar from '@/components/shared/ActionBar'
import StatsCard from '@/components/shared/StatsCard'
import SideSlider from '@/components/shared/SideSlider'
import { Button } from '@/components/ui'
import FilterComponent, { type FilterSelection } from '@/components/ui/FilterComponent'
import SearchComponent from '@/components/ui/SearchComponent'
import { getClasses } from '@/features/classes/services'
import { Capability } from '@/features/auth/capabilities'
import { useCan } from '@/features/auth/hooks/useCan'
import StudentsTable from '../components/StudentsTable'
import StudentOnboarding from '../components/student-onboarding/StudentOnboarding'
import { getStudentStats, getStudents } from '../services'
import type { StudentQueryParams } from '../types'

const GUARDIAN_FILTER_OPTIONS = [
  { value: true, label: 'Missing guardian' },
  { value: false, label: 'Has guardian' },
] as const

const NEW_STUDENT_FILTER_OPTIONS = [
  { value: true, label: 'New students' },
  { value: false, label: 'Continuing students' },
] as const

const booleanFromParam = (value: string | null): FilterSelection => {
  if (value === 'true') return true
  if (value === 'false') return false
  return ''
}

const Students = () => {
  const [search, setSearch] = useState('')
  const [classLevel, setClassLevel] = useState<FilterSelection>('')
  const [page, setPage] = useState(1)
  const [open, setOpen] = useState(false)
  const [searchParams, setSearchParams] = useSearchParams()
  const navigate = useNavigate()
  const canCreateStudent = useCan(Capability.STUDENTS_CREATE)

  const missingGuardian = booleanFromParam(searchParams.get('missing_guardian'))
  const isNewStudent = booleanFromParam(searchParams.get('is_new_student'))

  const setBooleanSearchParam = (key: string, value: FilterSelection) => {
    const next = new URLSearchParams(searchParams)
    if (value === true) next.set(key, 'true')
    else if (value === false) next.set(key, 'false')
    else next.delete(key)
    setSearchParams(next, { replace: true })
    setPage(1)
  }

  const queryParams: StudentQueryParams = useMemo(
    () => ({
      page,
      search: search || undefined,
      class_level: classLevel === '' ? undefined : String(classLevel),
      missing_guardian: typeof missingGuardian === 'boolean' ? missingGuardian : undefined,
      is_new_student: typeof isNewStudent === 'boolean' ? isNewStudent : undefined,
    }),
    [page, search, classLevel, missingGuardian, isNewStudent],
  )

  const { data, isLoading } = useQuery({
    queryKey: ['students', queryParams],
    queryFn: () => getStudents(queryParams),
  })

  const { data: stats } = useQuery({
    queryKey: ['students', 'stats'],
    queryFn: getStudentStats,
  })

  const { data: classes = [] } = useQuery({
    queryKey: ['classes'],
    queryFn: getClasses,
  })

  const classOptions = classes.map((item) => ({
    value: item.id,
    label: item.name,
  }))

  return (
    <div className="space-y-6">
      <ActionBar title="Students">
        <SearchComponent
          value={search}
          onChange={(value) => {
            setSearch(value)
            setPage(1)
          }}
        />
        <FilterComponent
          filterName="Class"
          filterKey="class_level"
          options={classOptions}
          value={classLevel}
          onChange={(value) => {
            setClassLevel(value)
            setPage(1)
          }}
        />
        <FilterComponent
          filterName="Guardian"
          filterKey="missing_guardian"
          options={[...GUARDIAN_FILTER_OPTIONS]}
          value={missingGuardian}
          placeholder="All students"
          onChange={(value) => setBooleanSearchParam('missing_guardian', value)}
        />
        <FilterComponent
          filterName="Enrollment"
          filterKey="is_new_student"
          options={[...NEW_STUDENT_FILTER_OPTIONS]}
          value={isNewStudent}
          placeholder="All students"
          onChange={(value) => setBooleanSearchParam('is_new_student', value)}
        />
        {canCreateStudent ? (
          <Button className="py-2 text-sm max-w-fit" onClick={() => setOpen(true)}>
            <Icon
              icon="hugeicons:plus-sign"
              className="size-4 bg-white text-black rounded-full p-0.5"
            />
            Add Student
          </Button>
        ) : null}
      </ActionBar>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsCard title="Total Students" value={String(stats?.total_students ?? 0)} />
        <StatsCard title="New Students (This Term)" value={String(stats?.new_students ?? 0)} />
        <StatsCard title="Boys" value={String(stats?.boys ?? 0)} />
        <StatsCard title="Girls" value={String(stats?.girls ?? 0)} />
      </div>

      <StudentsTable
        students={data?.results ?? []}
        isLoading={isLoading}
        pagination={data ?? null}
        onPageChange={setPage}
        onViewStudent={(student) => {
          navigate(`/students/${student.id}`)
        }}
      />

      {canCreateStudent ? (
        <SideSlider open={open} title="Student Onboarding" onClose={() => setOpen(false)}>
          <StudentOnboarding />
        </SideSlider>
      ) : null}
    </div>
  )
}

export default Students
