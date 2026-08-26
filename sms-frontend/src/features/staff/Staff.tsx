import { Icon } from '@iconify/react'
import { useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import ActionBar from '@/components/shared/ActionBar'
import StatsCard from '@/components/shared/StatsCard'
import { Button } from '@/components/ui'
import FilterComponent, { type FilterSelection } from '@/components/ui/FilterComponent'
import SearchComponent from '@/components/ui/SearchComponent'
import AddStaffFromDeskModal from './components/AddStaffFromDeskModal'
import StaffDeskTable from './components/StaffDeskTable'
import { getStaffDeskList, getStaffDeskStats } from './services'
import { STAFF_DESK_FILTER_OPTIONS, type StaffDeskQueryParams } from './types'
import { STAFF_DESK_QUERY_KEY } from './utils'

const Staff = () => {
  const navigate = useNavigate()
  const [search, setSearch] = useState('')
  const [role, setRole] = useState<FilterSelection>('')
  const [page, setPage] = useState(1)
  const [addOpen, setAddOpen] = useState(false)

  const queryParams: StaffDeskQueryParams = useMemo(
    () => ({
      page,
      search: search || undefined,
      role: role === '' ? undefined : String(role),
    }),
    [page, search, role],
  )

  const statsParams = useMemo(
    () => ({
      search: queryParams.search,
      role: queryParams.role,
    }),
    [queryParams.search, queryParams.role],
  )

  const { data, isLoading } = useQuery({
    queryKey: [STAFF_DESK_QUERY_KEY, 'list', queryParams],
    queryFn: () => getStaffDeskList(queryParams),
  })

  const { data: stats } = useQuery({
    queryKey: [STAFF_DESK_QUERY_KEY, 'stats', statsParams],
    queryFn: () => getStaffDeskStats(statsParams),
  })

  const openAdd = () => setAddOpen(true)

  return (
    <div className="space-y-6">
      <ActionBar title="Staff">
        <SearchComponent
          value={search}
          placeholder="Search staff..."
          onChange={(value) => {
            setSearch(value)
            setPage(1)
          }}
        />
        <FilterComponent
          filterName="Role"
          filterKey="role"
          options={[...STAFF_DESK_FILTER_OPTIONS]}
          value={role}
          placeholder="All Roles"
          onChange={(value) => {
            setRole(value)
            setPage(1)
          }}
        />
        <Button type="button" className="py-2 text-sm max-w-fit" onClick={openAdd}>
          <Icon
            icon="hugeicons:plus-sign"
            className="size-4 bg-white text-black rounded-full p-0.5"
          />
          Add Staff
        </Button>
      </ActionBar>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsCard title="Total Staff" value={String(stats?.total_staff ?? 0)} />
        <StatsCard title="Teachers" value={String(stats?.teachers ?? 0)} />
        <StatsCard title="Accountants" value={String(stats?.accountants ?? 0)} />
        <StatsCard title="Admins" value={String(stats?.admins ?? 0)} />
      </div>

      <StaffDeskTable
        rows={data?.results ?? []}
        isLoading={isLoading}
        pagination={data ?? null}
        onPageChange={setPage}
        onAddStaff={openAdd}
        onViewStaff={(row) => {
          navigate(`/staff/${row.id}`)
        }}
      />

      <AddStaffFromDeskModal open={addOpen} onClose={() => setAddOpen(false)} />
    </div>
  )
}

export default Staff
