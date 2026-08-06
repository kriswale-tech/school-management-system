import ActionBar from '@/components/shared/ActionBar'
import SearchComponent from '@/components/ui/SearchComponent'
import { Icon } from '@iconify/react/dist/iconify.cjs'
import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { Button } from '@/components/ui'
import StatsCard from '@/components/shared/StatsCard'
import ClassTable from '../components/ClassTable'
import { getClassList, getClassStats } from '../services'
import { useNavigate } from 'react-router-dom'

const Classes = () => {
  const [search, setSearch] = useState('')
  const navigate = useNavigate()
  const { data, isLoading } = useQuery({
    queryKey: ['classes', 'list', { search }],
    queryFn: () => getClassList({ search: search || undefined }),
  })

  const { data: stats } = useQuery({
    queryKey: ['classes', 'stats'],
    queryFn: getClassStats,
  })

  return (
    <div className="space-y-6">
      <ActionBar title="Classes">
        <SearchComponent value={search} onChange={setSearch} />
        <Button
          className="py-2 text-sm max-w-fit"
          onClick={() => navigate('/classes/manage')}
        >
          <Icon icon="hugeicons:settings-02" className="size-4" />
          Manage Classes
        </Button>
      </ActionBar>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsCard title="Total Classes" value={String(stats?.total_classes ?? 0)} />
        <StatsCard title="Total Students" value={String(stats?.total_students ?? 0)} />
        <StatsCard
          title="Unassigned Subjects"
          value={String(stats?.unassigned_class_subjects ?? 0)}
        />
        <StatsCard title="Unassigned Classes" value={String(stats?.unassigned_classes ?? 0)} />
      </div>

      <ClassTable
        classes={data?.results ?? []}
        isLoading={isLoading}
        onViewClass={(classItem) => {
          navigate(`/classes/${classItem.id}`)
        }}
      />
    </div>
  )
}

export default Classes
