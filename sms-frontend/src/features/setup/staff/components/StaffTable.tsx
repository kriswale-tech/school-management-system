import toast from 'react-hot-toast'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { ConfirmDialog, Table, TableWrapper } from '@/components/shared'
import ActionButton from '@/components/ui/ActionButton'
import AvatarComponent from '@/components/ui/AvatarComponent'
import EditStaffUserModal from '@/features/staff/components/EditStaffUserModal'
import { deleteStaff } from '@/features/staff/services'
import type { Staff } from '@/features/staff/types'
import { formatStaffRole, getStaffProfileImage } from '@/features/staff/utils'
import type { PaginatedResponse } from '@/types/generalTypes'
import { getApiErrorMessage } from '@/utils'

type StaffTableProps = {
  staff: Staff[]
  isLoading?: boolean
  pagination?: PaginatedResponse<Staff> | null
  onPageChange?: (page: number) => void
}

const deleteButtonClassName = 'text-red-600 hover:bg-red-50 hover:text-red-700'

const StaffTable = ({
  staff,
  isLoading = false,
  pagination = null,
  onPageChange,
}: StaffTableProps) => {
  const queryClient = useQueryClient()
  const [editingStaff, setEditingStaff] = useState<Staff | null>(null)
  const [deletingStaff, setDeletingStaff] = useState<Staff | null>(null)

  const { mutate: removeStaff, isPending: isDeleting } = useMutation({
    mutationFn: deleteStaff,
    onSuccess: () => {
      toast.success('Staff member deleted')
      void queryClient.invalidateQueries({ queryKey: ['staff'] })
      setDeletingStaff(null)
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, 'Unable to delete staff member'))
    },
  })

  return (
    <>
      <TableWrapper
        variant="form-field"
        isLoading={isLoading}
        isEmpty={!isLoading && staff.length === 0}
        emptyState={{
          title: 'No staff added yet',
          description: 'Select a staff role above to add admin, staff, or accountant users.',
        }}
        pagination={pagination}
        onPageChange={onPageChange}
        skeletonColumns={4}
      >
        <Table>
          <Table.Head>
            <Table.Row className="border-b-0">
              <Table.HeaderCell>User</Table.HeaderCell>
              <Table.HeaderCell>Contact</Table.HeaderCell>
              <Table.HeaderCell>Role</Table.HeaderCell>
              <Table.HeaderCell>Actions</Table.HeaderCell>
            </Table.Row>
          </Table.Head>
          <Table.Body>
            {staff.map((member) => (
              <Table.Row key={member.id}>
                <Table.Cell variant="primary">
                  <div className="flex items-center gap-3">
                    <AvatarComponent
                      image={getStaffProfileImage(member)}
                      fullName={member.full_name}
                      size={40}
                    />
                    <p>{member.full_name}</p>
                  </div>
                </Table.Cell>
                <Table.Cell>
                  <div className="space-y-1">
                    <p>{member.phone_number}</p>
                    <p className="text-xs text-slate-500">{member.email ?? '-'}</p>
                  </div>
                </Table.Cell>
                <Table.Cell>{formatStaffRole(member.role)}</Table.Cell>
                <Table.Cell>
                  <div className="flex shrink-0 items-center gap-1">
                    <ActionButton
                      icon="hugeicons:edit-02"
                      label={`Edit ${member.full_name}`}
                      onClick={() => setEditingStaff(member)}
                    />
                    <ActionButton
                      icon="hugeicons:delete-02"
                      label={`Delete ${member.full_name}`}
                      className={deleteButtonClassName}
                      onClick={() => setDeletingStaff(member)}
                    />
                  </div>
                </Table.Cell>
              </Table.Row>
            ))}
          </Table.Body>
        </Table>
      </TableWrapper>

      <EditStaffUserModal
        open={Boolean(editingStaff)}
        user={editingStaff}
        onClose={() => setEditingStaff(null)}
        invalidateQueryKey="staff"
        previewAlt="Staff profile photo preview"
      />

      <ConfirmDialog
        open={Boolean(deletingStaff)}
        title="Delete staff member"
        message={`Are you sure you want to delete "${deletingStaff?.full_name}"? This action cannot be undone.`}
        confirmLabel="Delete"
        onClose={() => setDeletingStaff(null)}
        onConfirm={() => {
          if (deletingStaff) removeStaff(deletingStaff.id)
        }}
        isLoading={isDeleting}
      />
    </>
  )
}

export default StaffTable
