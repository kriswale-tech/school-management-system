import { Table, TableWrapper } from '@/components/shared'
import ActionButton from '@/components/ui/ActionButton'
import type { StudentPayment } from '../types'
import { formatFeeAmount, formatStudentDate } from '../utils'

type PaymentHistoryTableProps = {
  payments?: StudentPayment[]
  isLoading?: boolean
}

const PaymentHistoryTable = ({ payments = [], isLoading = false }: PaymentHistoryTableProps) => {
  return (
    <TableWrapper
      isLoading={isLoading}
      isEmpty={!isLoading && payments.length === 0}
      emptyState={{
        title: 'No payments found',
        description: 'Payments recorded for this student will appear here.',
        icon: 'hugeicons:cash-01',
      }}
      skeletonColumns={5}
      variant="card"
    >
      <Table>
        <Table.Head>
          <Table.Row className="border-b-0">
            <Table.HeaderCell>Term</Table.HeaderCell>
            <Table.HeaderCell>Payment mode</Table.HeaderCell>
            <Table.HeaderCell>Amount</Table.HeaderCell>
            <Table.HeaderCell>Payment date</Table.HeaderCell>
            <Table.HeaderCell>Receipt</Table.HeaderCell>
          </Table.Row>
        </Table.Head>
        <Table.Body>
          {payments.map((payment) => (
            <Table.Row key={payment.id}>
              <Table.Cell>
                <div className="space-y-1">
                  <p>{payment.term_name}</p>
                  <p className="text-xs text-slate-500">{payment.academic_year}</p>
                </div>
              </Table.Cell>
              <Table.Cell>{payment.payment_method_display}</Table.Cell>
              <Table.Cell>{formatFeeAmount(payment.amount)}</Table.Cell>
              <Table.Cell>{formatStudentDate(payment.paid_at)}</Table.Cell>
              <Table.Cell>
                {payment.receipt ? (
                  <ActionButton
                    icon="hugeicons:view"
                    label={`View receipt ${payment.receipt.receipt_number}`}
                  />
                ) : (
                  <span className="text-sm text-slate-400">—</span>
                )}
              </Table.Cell>
            </Table.Row>
          ))}
        </Table.Body>
      </Table>
    </TableWrapper>
  )
}

export default PaymentHistoryTable
