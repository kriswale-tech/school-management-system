import { useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Table, TableWrapper } from '@/components/shared'
import ActionButton from '@/components/ui/ActionButton'
import { Capability } from '@/features/auth/capabilities'
import { useCan } from '@/features/auth/hooks'
import type { SubjectClassPairing } from '../types'
import AssignSubjectTeacher from './AssignSubjectTeacher'

type SubjectClassTableProps = {
  subjects?: SubjectClassPairing[]
  isLoading?: boolean
}

const SubjectClassTable = ({ subjects = [], isLoading = false }: SubjectClassTableProps) => {
  const canManageClasses = useCan(Capability.CLASSES_MANAGE)
  const queryClient = useQueryClient()
  const [selectedSubject, setSelectedSubject] = useState<SubjectClassPairing | null>(null)

  return (
    <>
      <TableWrapper
        isLoading={isLoading}
        isEmpty={!isLoading && subjects.length === 0}
        emptyState={{
          title: 'No subjects yet',
          description: 'Subjects taught in each class will appear here once configured.',
          icon: 'hugeicons:book-02',
        }}
        skeletonColumns={canManageClasses ? 6 : 5}
        variant="card"
      >
        <Table>
          <Table.Head>
            <Table.Row className="border-b-0">
              <Table.HeaderCell>Subject</Table.HeaderCell>
              <Table.HeaderCell>Group</Table.HeaderCell>
              <Table.HeaderCell>Class</Table.HeaderCell>
              <Table.HeaderCell>Students</Table.HeaderCell>
              <Table.HeaderCell>Subject Teacher</Table.HeaderCell>
              {canManageClasses ? <Table.HeaderCell>Action</Table.HeaderCell> : null}
            </Table.Row>
          </Table.Head>
          <Table.Body>
            {subjects.map((subject) => {
              const hasTeacher = Boolean(subject.teacher)
              const actionLabel = hasTeacher
                ? `Reassign subject teacher for ${subject.name}`
                : `Assign subject teacher for ${subject.name}`

              return (
                <Table.Row key={subject.id}>
                  <Table.Cell variant="primary">{subject.subject_name}</Table.Cell>
                  <Table.Cell>{subject.group_name ?? '-'}</Table.Cell>
                  <Table.Cell>
                    <div className="space-y-1">
                      <p>{subject.class_name}</p>
                      {subject.needs_attention ? (
                        <p className="text-xs font-medium text-red-600">Needs attention</p>
                      ) : null}
                    </div>
                  </Table.Cell>
                  <Table.Cell>{subject.students_count}</Table.Cell>
                  <Table.Cell>{subject.teacher?.full_name ?? '-'}</Table.Cell>
                  {canManageClasses ? (
                    <Table.Cell>
                      <ActionButton
                        icon={hasTeacher ? 'hugeicons:user-switch' : 'hugeicons:user-add-01'}
                        label={actionLabel}
                        onClick={() => setSelectedSubject(subject)}
                      />
                    </Table.Cell>
                  ) : null}
                </Table.Row>
              )
            })}
          </Table.Body>
        </Table>
      </TableWrapper>

      {canManageClasses ? (
        <AssignSubjectTeacher
          open={Boolean(selectedSubject)}
          streamId={selectedSubject?.stream_id ?? ''}
          subject={selectedSubject}
          classLabel={selectedSubject?.class_name}
          onClose={() => setSelectedSubject(null)}
          onAssigned={() => {
            setSelectedSubject(null)
            void queryClient.invalidateQueries({ queryKey: ['classes', 'subjects'] })
            void queryClient.invalidateQueries({ queryKey: ['classes', 'stats'] })
          }}
        />
      ) : null}
    </>
  )
}

export default SubjectClassTable
