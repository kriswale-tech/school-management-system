import { Icon } from '@iconify/react'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import ActionBar from '@/components/shared/ActionBar'
import StatsCard from '@/components/shared/StatsCard'
import { Button } from '@/components/ui'
import FilterComponent, { type FilterSelection } from '@/components/ui/FilterComponent'
import SearchComponent from '@/components/ui/SearchComponent'
import { getClasses } from '@/features/classes/services'
import StudentsTable from '../components/StudentsTable'
import { getStudentStats, getStudents } from '../services'
import type { StudentQueryParams } from '../types'
import SideSlider from '@/components/shared/SideSlider'
import StudentOnboarding from '../components/student-onboarding/StudentOnboarding'

const Students = () => {
  const [search, setSearch] = useState('')
  const [classLevel, setClassLevel] = useState<FilterSelection>('')
  const [page, setPage] = useState(1)
  const [open, setOpen] = useState(false)

  const queryParams: StudentQueryParams = {
    page,
    search: search || undefined,
    class_level: classLevel === '' ? undefined : String(classLevel),
  }

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
        <Button className="py-2 text-sm max-w-fit" onClick={() => setOpen(true)}>
          <Icon
            icon="hugeicons:plus-sign"
            className="size-4 bg-white text-black rounded-full p-0.5"
          />
          Add Student
        </Button>
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
      />

      <SideSlider open={open} title="Student Onboarding" onClose={() => setOpen(false)}>
        <StudentOnboarding />
      </SideSlider>
    </div>
  )
}

export default Students
