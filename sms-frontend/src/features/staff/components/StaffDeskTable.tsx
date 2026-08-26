import { Table, TableWrapper } from '@/components/shared'
import ActionButton from '@/components/ui/ActionButton'
import AvatarComponent from '@/components/ui/AvatarComponent'
import type { PaginatedResponse } from '@/types/generalTypes'
import type { StaffDeskRow } from '../types'
import {
  formatStaffDate,
  formatStaffRoleSubtitle,
  getStaffDeskProfileImage,
} from '../utils'

type StaffDeskTableProps = {
  rows?: StaffDeskRow[]
  isLoading?: boolean
  pagination?: PaginatedResponse<StaffDeskRow> | null
  onPageChange?: (page: number) => void
  onAddStaff?: () => void
  onViewStaff?: (row: StaffDeskRow) => void
}

const StaffDeskTable = ({
  rows = [],
  isLoading = false,
  pagination = null,
  onPageChange,
  onAddStaff,
  onViewStaff,
}: StaffDeskTableProps) => {
  return (
    <TableWrapper
      isLoading={isLoading}
      isEmpty={!isLoading && rows.length === 0}
      emptyState={{
        title: 'No staff found',
        description: 'Try adjusting your search or role filter, or add a staff member.',
        actionLabel: onAddStaff ? 'Add Staff' : undefined,
        onAction: onAddStaff,
        icon: 'hugeicons:user-group',
      }}
      pagination={pagination}
      onPageChange={onPageChange}
      skeletonColumns={5}
      variant="card"
    >
      <Table>
        <Table.Head>
          <Table.Row className="border-b-0">
            <Table.HeaderCell>Staff</Table.HeaderCell>
            <Table.HeaderCell>Contact</Table.HeaderCell>
            <Table.HeaderCell>Status</Table.HeaderCell>
            <Table.HeaderCell>Date added</Table.HeaderCell>
            <Table.HeaderCell>Action</Table.HeaderCell>
          </Table.Row>
        </Table.Head>
        <Table.Body>
          {rows.map((row) => (
            <Table.Row key={row.id}>
              <Table.Cell variant="primary">
                <div className="flex items-center gap-3">
                  <AvatarComponent
                    image={getStaffDeskProfileImage(row)}
                    fullName={row.full_name}
                    size={40}
                  />
                  <div className="space-y-1">
                    <p>{row.full_name}</p>
                    <p className="text-xs font-normal text-slate-500">
                      {formatStaffRoleSubtitle(row)}
                    </p>
                  </div>
                </div>
              </Table.Cell>
              <Table.Cell>
                <div className="space-y-1">
                  <p>{row.email?.trim() || '—'}</p>
                  <p className="text-xs text-slate-500">{row.phone_number}</p>
                </div>
              </Table.Cell>
              <Table.Cell>
                <span className={row.is_active ? 'text-green-600' : 'text-slate-500'}>
                  {row.is_active ? 'Active' : 'Inactive'}
                </span>
              </Table.Cell>
              <Table.Cell>{formatStaffDate(row.date_added)}</Table.Cell>
              <Table.Cell>
                <ActionButton
                  icon="hugeicons:view"
                  label={`View ${row.full_name}`}
                  onClick={() => onViewStaff?.(row)}
                />
              </Table.Cell>
            </Table.Row>
          ))}
        </Table.Body>
      </Table>
    </TableWrapper>
  )
}

export default StaffDeskTable
