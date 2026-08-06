import { Table, TableWrapper } from '@/components/shared'
import ActionButton from '@/components/ui/ActionButton'
import type { ClassListItem } from '../types'

type ClassTableProps = {
  classes?: ClassListItem[]
  isLoading?: boolean
  onViewClass?: (classItem: ClassListItem) => void
}

const ClassTable = ({ classes = [], isLoading = false, onViewClass }: ClassTableProps) => {
  return (
    <TableWrapper
      isLoading={isLoading}
      isEmpty={!isLoading && classes.length === 0}
      emptyState={{
        title: 'No classes added yet',
        description: 'Create classes to organize students, subjects, and class teachers.',
        icon: 'hugeicons:school',
      }}
      skeletonColumns={6}
      variant="card"
    >
      <Table>
        <Table.Head>
          <Table.Row className="border-b-0">
            <Table.HeaderCell>Class</Table.HeaderCell>
            <Table.HeaderCell>Level</Table.HeaderCell>
            <Table.HeaderCell>Students</Table.HeaderCell>
            <Table.HeaderCell>Subjects</Table.HeaderCell>
            <Table.HeaderCell>Class Teacher</Table.HeaderCell>
            <Table.HeaderCell>Action</Table.HeaderCell>
          </Table.Row>
        </Table.Head>
        <Table.Body>
          {classes.map((classItem) => (
            <Table.Row key={classItem.id}>
              <Table.Cell variant="primary">
                <div className="space-y-1">
                  <p>{classItem.name}</p>
                  {classItem.needs_attention ? (
                    <p className="text-xs font-medium text-red-600">Needs attention</p>
                  ) : null}
                </div>
              </Table.Cell>
              <Table.Cell>{classItem.level_name}</Table.Cell>
              <Table.Cell>{classItem.students_count}</Table.Cell>
              <Table.Cell>{classItem.subjects_count}</Table.Cell>
              <Table.Cell>{classItem.class_teacher?.full_name ?? '-'}</Table.Cell>
              <Table.Cell>
                <ActionButton
                  icon="hugeicons:view"
                  label={`View ${classItem.name}`}
                  onClick={() => onViewClass?.(classItem)}
                />
              </Table.Cell>
            </Table.Row>
          ))}
        </Table.Body>
      </Table>
    </TableWrapper>
  )
}

export default ClassTable
