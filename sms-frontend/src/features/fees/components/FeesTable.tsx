import { Table, TableWrapper } from '@/components/shared'
import ActionButton from '@/components/ui/ActionButton'
import AvatarComponent from '@/components/ui/AvatarComponent'
import type { PaginatedResponse } from '@/types/generalTypes'
import type { FeeDeskRow } from '../types'
import {
  formatFeeAmount,
  formatFeeTransactionDate,
  getFeeDeskFullName,
  isFeeDeskDebtor,
} from '../utils'

type FeesTableProps = {
  rows?: FeeDeskRow[]
  isLoading?: boolean
  pagination?: PaginatedResponse<FeeDeskRow> | null
  onPageChange?: (page: number) => void
  onViewRow?: (row: FeeDeskRow) => void
  selectionEnabled?: boolean
  selectedIds?: Set<string>
  onToggleRow?: (row: FeeDeskRow) => void
  selectAllChecked?: boolean
  selectAllIndeterminate?: boolean
  selectAllLoading?: boolean
  onToggleSelectAll?: () => void
}

const FeesTable = ({
  rows = [],
  isLoading = false,
  pagination = null,
  onPageChange,
  onViewRow,
  selectionEnabled = false,
  selectedIds = new Set(),
  onToggleRow,
  selectAllChecked = false,
  selectAllIndeterminate = false,
  selectAllLoading = false,
  onToggleSelectAll,
}: FeesTableProps) => {
  return (
    <TableWrapper
      isLoading={isLoading}
      isEmpty={!isLoading && rows.length === 0}
      emptyState={{
        title: 'No fee records found',
        description: 'Try adjusting your search or filters, or enroll students for this term.',
        icon: 'hugeicons:cash-01',
      }}
      pagination={pagination}
      onPageChange={onPageChange}
      skeletonColumns={selectionEnabled ? 6 : 5}
      variant="card"
    >
      <Table>
        <Table.Head>
          <Table.Row className="border-b-0">
            {selectionEnabled ? (
              <Table.HeaderCell className="w-12">
                <input
                  type="checkbox"
                  aria-label="Select all matching debtors"
                  title="Select all matching debtors across pages"
                  className="size-4 rounded border-slate-400"
                  checked={selectAllChecked}
                  ref={(el) => {
                    if (el) el.indeterminate = selectAllIndeterminate
                  }}
                  disabled={selectAllLoading}
                  onChange={() => onToggleSelectAll?.()}
                />
              </Table.HeaderCell>
            ) : null}
            <Table.HeaderCell>Student</Table.HeaderCell>
            <Table.HeaderCell>Amount paid</Table.HeaderCell>
            <Table.HeaderCell>Remaining balance</Table.HeaderCell>
            <Table.HeaderCell>Last transaction</Table.HeaderCell>
            <Table.HeaderCell>Action</Table.HeaderCell>
          </Table.Row>
        </Table.Head>
        <Table.Body>
          {rows.map((row) => {
            const fullName = getFeeDeskFullName(row)
            const classLabel = row.stream?.full_name ?? row.class_level?.name ?? '—'
            const canSelect = selectionEnabled && isFeeDeskDebtor(row.remaining_balance)
            const checked = selectedIds.has(row.id)

            return (
              <Table.Row key={row.id}>
                {selectionEnabled ? (
                  <Table.Cell>
                    <input
                      type="checkbox"
                      aria-label={`Select ${fullName}`}
                      className="size-4 rounded border-slate-400 disabled:cursor-not-allowed disabled:opacity-40"
                      checked={checked}
                      disabled={!canSelect}
                      onChange={() => onToggleRow?.(row)}
                    />
                  </Table.Cell>
                ) : null}
                <Table.Cell variant="primary">
                  <div className="flex items-center gap-3">
                    <AvatarComponent fullName={fullName} size={40} />
                    <div className="space-y-1">
                      <p>{fullName}</p>
                      <p className="text-xs font-normal text-slate-500">{classLabel}</p>
                    </div>
                  </div>
                </Table.Cell>
                <Table.Cell>{formatFeeAmount(row.amount_paid)}</Table.Cell>
                <Table.Cell>
                  <div className="space-y-1">
                    <p
                      className={
                        Number(row.remaining_balance) > 0 ? 'font-medium text-red-600' : undefined
                      }
                    >
                      {formatFeeAmount(row.remaining_balance)}
                    </p>
                  </div>
                </Table.Cell>
                <Table.Cell>{formatFeeTransactionDate(row.last_transaction_at)}</Table.Cell>
                <Table.Cell>
                  <ActionButton
                    icon="hugeicons:view"
                    label="View"
                    onClick={() => onViewRow?.(row)}
                  />
                </Table.Cell>
              </Table.Row>
            )
          })}
        </Table.Body>
      </Table>
    </TableWrapper>
  )
}

export default FeesTable
