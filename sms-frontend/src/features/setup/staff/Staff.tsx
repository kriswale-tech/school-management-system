import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'
import { useOutletContext } from 'react-router-dom'
import AddStaffUserModal from '@/features/staff/components/AddStaffUserModal'
import { getStaff } from '@/features/staff/services'
import Button from '@/components/ui/Button'
import CompleteSetupModal from '@/features/setup/components/CompleteSetupModal'
import type { Setup } from '@/features/setup/types/types'
import StaffRoleCard from './components/StaffRoleCard'
import StaffTable from './components/StaffTable'
import { Icon } from '@iconify/react/dist/iconify.cjs'

const STAFF_ROLES = [
  {
    title: 'Admin',
    description: 'Full access to all school operations and management.',
    image: '/icons/admin.svg',
    value: 'admin',
  },
  {
    title: 'Staff',
    description: 'Non-teaching administrative staff with limited access.',
    image: '/icons/staff.svg',
    value: 'staff',
  },
  {
    title: 'Accountant',
    description: 'Access strictly to fee management, financial reports, and invoicing.',
    image: '/icons/accountant.svg',
    value: 'accountant',
  },
]

const Staff = () => {
  const setup = useOutletContext<Setup>()
  const [page, setPage] = useState(1)
  const [selectedRole, setSelectedRole] = useState<(typeof STAFF_ROLES)[number] | null>(null)
  const [isAddModalOpen, setIsAddModalOpen] = useState(false)
  const [isCompleteModalOpen, setIsCompleteModalOpen] = useState(false)
  const [addModalSession, setAddModalSession] = useState(0)

  const { data, isLoading } = useQuery({
    queryKey: ['staff', page],
    queryFn: () => getStaff({ page, exclude: 'teacher' }),
  })

  const handleRoleClick = (role: (typeof STAFF_ROLES)[number]) => {
    setSelectedRole(role)
    setAddModalSession((session) => session + 1)
    setIsAddModalOpen(true)
  }

  const closeAddModal = () => {
    setIsAddModalOpen(false)
    setSelectedRole(null)
  }

  return (
    <div className="space-y-6">
      <div>
        <div className="flex justify-between gap-4 mb-2 ">
          <h2 className="text-lg text-slate-900  shrink-0">Select Staff Role</h2>
          <p className="flex items-center gap-1 text-blue-500 text-sm">
            <Icon icon="hugeicons:information-circle" className="size-4 " />{' '}
            <span>You can skip this step if you don't have any staff yet</span>
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {STAFF_ROLES.map((role) => (
            <StaffRoleCard key={role.value} role={role} onClick={handleRoleClick} />
          ))}
        </div>
      </div>

      <StaffTable
        staff={data?.results ?? []}
        isLoading={isLoading}
        pagination={data ?? null}
        onPageChange={setPage}
      />

      {selectedRole ? (
        <AddStaffUserModal
          open={isAddModalOpen}
          onClose={closeAddModal}
          sessionKey={addModalSession}
          role={selectedRole.value}
          title={`Add ${selectedRole.title}`}
          submitLabel={`Add ${selectedRole.title}`}
          successMessage={`${selectedRole.title} added`}
          invalidateQueryKey="staff"
          previewAlt="Staff profile photo preview"
        />
      ) : null}

      <Button type="button" variant="solid" onClick={() => setIsCompleteModalOpen(true)}>
        Complete Setup
      </Button>

      <CompleteSetupModal
        open={isCompleteModalOpen}
        onClose={() => setIsCompleteModalOpen(false)}
        setup={setup}
      />
    </div>
  )
}

export default Staff
