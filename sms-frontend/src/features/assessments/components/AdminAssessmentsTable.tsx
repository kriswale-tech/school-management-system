import { Table, TableWrapper } from '@/components/shared'
import ActionButton from '@/components/ui/ActionButton'
import { mergeClasses } from '@/utils'
import type { PaginatedResponse } from '@/types/generalTypes'
import type { AdminAssessmentClassRow } from '@/features/classes/assessment/types'

type AdminAssessmentsTableProps = {
  rows?: AdminAssessmentClassRow[]
  isLoading?: boolean
  pagination?: PaginatedResponse<AdminAssessmentClassRow> | null
  onPageChange?: (page: number) => void
  onViewClass?: (_row: AdminAssessmentClassRow) => void
}

type ClassBadge = {
  label: string
  tone: 'amber' | 'blue' | 'green'
}

const classBadge = (row: AdminAssessmentClassRow): ClassBadge => {
  if (row.with_class_teacher_count > 0) {
    const count = row.with_class_teacher_count
    return {
      tone: 'amber',
      label: `Not complete · ${count} with class teacher`,
    }
  }
  if (
    row.students_count > 0 &&
    row.ready_for_you_count === 0 &&
    row.released_count === row.students_count
  ) {
    return { tone: 'green', label: 'Released' }
  }
  return { tone: 'blue', label: 'All in' }
}

const badgeClassName = (tone: ClassBadge['tone']) =>
  mergeClasses(
    'inline-flex rounded-md px-2 py-0.5 text-xs font-medium',
    tone === 'amber' && 'bg-amber-50 text-amber-800',
    tone === 'blue' && 'bg-blue-50 text-blue-800',
    tone === 'green' && 'bg-emerald-50 text-emerald-800',
  )

const countClassName = (tone: 'blue' | 'green') =>
  mergeClasses(
    'font-medium',
    tone === 'blue' && 'text-blue-700',
    tone === 'green' && 'text-emerald-700',
  )

const AdminAssessmentsTable = ({
  rows = [],
  isLoading = false,
  pagination = null,
  onPageChange,
  onViewClass,
}: AdminAssessmentsTableProps) => {
  return (
    <TableWrapper
      isLoading={isLoading}
      isEmpty={!isLoading && rows.length === 0}
      emptyState={{
        title: 'Nothing waiting on you',
        description: 'Classes appear here once a class teacher has approved at least one student.',
        icon: 'hugeicons:school',
      }}
      pagination={pagination}
      onPageChange={onPageChange}
      skeletonColumns={4}
      variant="form-field"
    >
      <Table>
        <Table.Head>
          <Table.Row className="border-b-0">
            <Table.HeaderCell>Class</Table.HeaderCell>
            <Table.HeaderCell className="text-blue-700">Ready for you</Table.HeaderCell>
            <Table.HeaderCell className="text-emerald-700">Released</Table.HeaderCell>
            <Table.HeaderCell>Action</Table.HeaderCell>
          </Table.Row>
        </Table.Head>
        <Table.Body>
          {rows.map((row) => {
            const badge = classBadge(row)
            return (
              <Table.Row key={row.id}>
                <Table.Cell variant="primary">
                  <div className="space-y-1">
                    <p>{row.display_name}</p>
                    <p className="text-xs font-normal text-slate-500">
                      {row.class_teacher_name ?? 'No class teacher'}
                    </p>
                    <span className={badgeClassName(badge.tone)}>{badge.label}</span>
                  </div>
                </Table.Cell>
                <Table.Cell className={countClassName('blue')}>{row.ready_for_you_count}</Table.Cell>
                <Table.Cell className={countClassName('green')}>{row.released_count}</Table.Cell>
                <Table.Cell>
                  <ActionButton
                    icon="hugeicons:view"
                    label={`View ${row.display_name}`}
                    onClick={() => onViewClass?.(row)}
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

export default AdminAssessmentsTable
