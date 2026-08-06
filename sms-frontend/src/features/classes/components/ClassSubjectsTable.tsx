import { useState } from 'react'
import { Table, TableWrapper } from '@/components/shared'
import ActionButton from '@/components/ui/ActionButton'
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
        skeletonColumns={4}
        variant="form-field"
      >
        <Table>
          <Table.Head>
            <Table.Row className="border-b-0">
              <Table.HeaderCell>Subject</Table.HeaderCell>
              <Table.HeaderCell>Number of Students</Table.HeaderCell>
              <Table.HeaderCell>Subject Teacher</Table.HeaderCell>
              <Table.HeaderCell>Action</Table.HeaderCell>
            </Table.Row>
          </Table.Head>
          <Table.Body>
            {subjects.map((subject) => (
              <Table.Row key={`${subject.kind}-${subject.id}`}>
                <Table.Cell variant="primary">{subject.name}</Table.Cell>
                <Table.Cell>{subject.students_count}</Table.Cell>
                <Table.Cell>{subject.teacher?.full_name ?? '-'}</Table.Cell>
                <Table.Cell>
                  <ActionButton
                    icon="hugeicons:user-switch"
                    label="Change Subject Teacher"
                    onClick={() => setSelectedSubject(subject)}
                  />
                </Table.Cell>
              </Table.Row>
            ))}
          </Table.Body>
        </Table>
      </TableWrapper>

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
    </>
  )
}

export default ClassSubjectsTable
