import { Table, TableWrapper } from '@/components/shared'
import ActionButton from '@/components/ui/ActionButton'
import { mergeClasses } from '@/utils'

export type ClassTeacherAssessmentRow = {
  id: string
  class_level_id: string
  class_level_name: string
  stream_id: string | null
  stream_name: string | null
  display_name: string
  students_count: number
  view_stream_id: string | null
  pending_count: number
  ready_count: number
  approved_count: number
  needs_correction_count: number
}

type ClassTeacherAssessmentsTableProps = {
  rows?: ClassTeacherAssessmentRow[]
  isLoading?: boolean
  onViewClass?: (_row: ClassTeacherAssessmentRow) => void
}

const countClassName = (tone: 'amber' | 'blue' | 'green' | 'orange') =>
  mergeClasses(
    'font-medium',
    tone === 'amber' && 'text-amber-700',
    tone === 'blue' && 'text-blue-700',
    tone === 'green' && 'text-emerald-700',
    tone === 'orange' && 'text-orange-700',
  )

const ClassTeacherAssessmentsTable = ({
  rows = [],
  isLoading = false,
  onViewClass,
}: ClassTeacherAssessmentsTableProps) => {
  return (
    <TableWrapper
      isLoading={isLoading}
      isEmpty={!isLoading && rows.length === 0}
      emptyState={{
        title: 'No managed classes',
        description: 'Classes where you are the class teacher will appear here.',
        icon: 'hugeicons:school',
      }}
      skeletonColumns={6}
      variant="form-field"
    >
      <Table>
        <Table.Head>
          <Table.Row className="border-b-0">
            <Table.HeaderCell>Class</Table.HeaderCell>
            <Table.HeaderCell>Students</Table.HeaderCell>
            <Table.HeaderCell className="text-amber-700">Pending</Table.HeaderCell>
            <Table.HeaderCell className="text-blue-700">Awaiting approval</Table.HeaderCell>
            <Table.HeaderCell className="text-emerald-700">Approved</Table.HeaderCell>
            <Table.HeaderCell className="text-orange-700">Corrections</Table.HeaderCell>
            <Table.HeaderCell>Action</Table.HeaderCell>
          </Table.Row>
        </Table.Head>
        <Table.Body>
          {rows.map((row) => (
            <Table.Row key={row.id}>
              <Table.Cell variant="primary">{row.display_name}</Table.Cell>
              <Table.Cell>{row.students_count}</Table.Cell>
              <Table.Cell className={countClassName('amber')}>{row.pending_count}</Table.Cell>
              <Table.Cell className={countClassName('blue')}>{row.ready_count}</Table.Cell>
              <Table.Cell className={countClassName('green')}>{row.approved_count}</Table.Cell>
              <Table.Cell className={countClassName('orange')}>
                {row.needs_correction_count}
              </Table.Cell>
              <Table.Cell>
                <ActionButton
                  icon="hugeicons:view"
                  label={`View ${row.display_name}`}
                  onClick={() => onViewClass?.(row)}
                />
              </Table.Cell>
            </Table.Row>
          ))}
        </Table.Body>
      </Table>
    </TableWrapper>
  )
}

export default ClassTeacherAssessmentsTable
