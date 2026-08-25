import { Table, TableWrapper } from '@/components/shared'
import ActionButton from '@/components/ui/ActionButton'
import AvatarComponent from '@/components/ui/AvatarComponent'
import type { PaginatedResponse } from '@/types/generalTypes'
import type { FeeDeskRow } from '../types'
import { formatFeeAmount, formatFeeTransactionDate, getFeeDeskFullName } from '../utils'

type FeesTableProps = {
  rows?: FeeDeskRow[]
  isLoading?: boolean
  pagination?: PaginatedResponse<FeeDeskRow> | null
  onPageChange?: (page: number) => void
  onViewRow?: (row: FeeDeskRow) => void
}

const FeesTable = ({
  rows = [],
  isLoading = false,
  pagination = null,
  onPageChange,
  onViewRow,
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
      skeletonColumns={5}
      variant="card"
    >
      <Table>
        <Table.Head>
          <Table.Row className="border-b-0">
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

            return (
              <Table.Row key={row.id}>
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
                    <p>{formatFeeAmount(row.remaining_balance)}</p>
                    {Number(row.advance_balance) > 0 ? (
                      <p className="text-xs font-medium text-emerald-700">
                        Advance {formatFeeAmount(row.advance_balance)}
                      </p>
                    ) : null}
                  </div>
                </Table.Cell>
                <Table.Cell>{formatFeeTransactionDate(row.last_transaction_at)}</Table.Cell>
                <Table.Cell>
                  <ActionButton
                    icon="hugeicons:view"
                    label={`View fees for ${fullName}`}
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
