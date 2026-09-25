import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Table, TableWrapper } from '@/components/shared'
import ActionButton from '@/components/ui/ActionButton'
import { Capability } from '@/features/auth/capabilities'
import { useCan } from '@/features/auth/hooks'
import type { ClassListItem } from '../types'
import AssignClassTeacher from './AssignClassTeacher'

type ClassTableProps = {
  classes?: ClassListItem[]
  isLoading?: boolean
  onViewClass?: (classItem: ClassListItem) => void
}

const ClassTable = ({ classes = [], isLoading = false, onViewClass }: ClassTableProps) => {
  const canManageClasses = useCan(Capability.CLASSES_MANAGE)
  const queryClient = useQueryClient()
  const [selectedClass, setSelectedClass] = useState<ClassListItem | null>(null)

  return (
    <>
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
                  <div className="flex items-center gap-2">
                    {canManageClasses ? (
                      <ActionButton
                        icon={
                          classItem.class_teacher
                            ? 'hugeicons:user-switch'
                            : 'hugeicons:user-add-01'
                        }
                        label={
                          classItem.class_teacher
                            ? `Reassign class teacher for ${classItem.name}`
                            : `Assign class teacher for ${classItem.name}`
                        }
                        onClick={() => setSelectedClass(classItem)}
                      />
                    ) : null}
                    <ActionButton
                      icon="hugeicons:view"
                      label={`View ${classItem.name}`}
                      onClick={() => onViewClass?.(classItem)}
                    />
                  </div>
                </Table.Cell>
              </Table.Row>
            ))}
          </Table.Body>
        </Table>
      </TableWrapper>

      {canManageClasses ? (
        <AssignClassTeacher
          open={Boolean(selectedClass)}
          streamId={selectedClass?.id ?? ''}
          classDisplayName={selectedClass?.name}
          selectedTeacherId={selectedClass?.class_teacher?.id ?? null}
          onClose={() => setSelectedClass(null)}
          onAssigned={() => {
            setSelectedClass(null)
            void queryClient.invalidateQueries({ queryKey: ['classes', 'list'] })
            void queryClient.invalidateQueries({ queryKey: ['classes', 'stats'] })
          }}
        />
      ) : null}
    </>
  )
}

export default ClassTable
