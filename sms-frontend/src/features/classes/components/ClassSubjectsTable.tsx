import { useState } from 'react'
import { Table, TableWrapper } from '@/components/shared'
import ActionButton from '@/components/ui/ActionButton'
import { Capability } from '@/features/auth/capabilities'
import { useCan } from '@/features/auth/hooks'
import type { ClassSubjectRow } from '../types'
import AssignSubjectTeacher from './AssignSubjectTeacher'

type ClassSubjectsTableProps = {
  streamId: string
  subjects?: ClassSubjectRow[]
  isLoading?: boolean
  onAssigned?: () => void
}

const ClassSubjectsTable = ({
  streamId,
  subjects = [],
  isLoading = false,
  onAssigned,
}: ClassSubjectsTableProps) => {
  const canManageClasses = useCan(Capability.CLASSES_MANAGE)
  const [selectedSubject, setSelectedSubject] = useState<ClassSubjectRow | null>(null)

  return (
    <>
      <TableWrapper
        isLoading={isLoading}
        isEmpty={!isLoading && subjects.length === 0}
        emptyState={{
          title: 'No subjects assigned',
          description: 'Subjects for this class will appear here once configured.',
          icon: 'hugeicons:book-02',
        }}
        skeletonColumns={canManageClasses ? 4 : 3}
        variant="form-field"
      >
        <Table>
          <Table.Head>
            <Table.Row className="border-b-0">
              <Table.HeaderCell>Subject</Table.HeaderCell>
              <Table.HeaderCell>Number of Students</Table.HeaderCell>
              <Table.HeaderCell>Subject Teacher</Table.HeaderCell>
              {canManageClasses ? <Table.HeaderCell>Action</Table.HeaderCell> : null}
            </Table.Row>
          </Table.Head>
          <Table.Body>
            {subjects.map((subject) => (
              <Table.Row key={`${subject.kind}-${subject.id}`}>
                <Table.Cell variant="primary">{subject.name}</Table.Cell>
                <Table.Cell>{subject.students_count}</Table.Cell>
                <Table.Cell>{subject.teacher?.full_name ?? '-'}</Table.Cell>
                {canManageClasses ? (
                  <Table.Cell>
                    <ActionButton
                      icon="hugeicons:user-switch"
                      label="Change Subject Teacher"
                      onClick={() => setSelectedSubject(subject)}
                    />
                  </Table.Cell>
                ) : null}
              </Table.Row>
            ))}
          </Table.Body>
        </Table>
      </TableWrapper>

      {canManageClasses ? (
        <AssignSubjectTeacher
          open={Boolean(selectedSubject)}
          streamId={streamId}
          subject={selectedSubject}
          onClose={() => setSelectedSubject(null)}
          onAssigned={() => {
            setSelectedSubject(null)
            onAssigned?.()
          }}
        />
      ) : null}
    </>
  )
}

export default ClassSubjectsTable
