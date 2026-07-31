import { Table, TableWrapper } from '@/components/shared'
import ActionButton from '@/components/ui/ActionButton'
import AvatarComponent from '@/components/ui/AvatarComponent'
import dayjs from '@/lib/dayjs'
import type { PaginatedResponse } from '@/types/generalTypes'
import type { Student } from '../types'

type StudentsTableProps = {
  students?: Student[]
  isLoading?: boolean
  pagination?: PaginatedResponse<Student> | null
  onPageChange?: (page: number) => void
  onAddStudent?: () => void
  onViewStudent?: (student: Student) => void
}

const getStudentFullName = (student: Student) =>
  [student.first_name, student.other_names, student.last_name].filter(Boolean).join(' ')

const formatAdmissionDate = (value: string) => {
  const date = dayjs(value)
  return date.isValid() ? date.format('DD MMM YYYY') : '-'
}

const StudentsTable = ({
  students = [],
  isLoading = false,
  pagination = null,
  onPageChange,
  onAddStudent,
  onViewStudent,
}: StudentsTableProps) => {
  return (
    <TableWrapper
      isLoading={isLoading}
      isEmpty={!isLoading && students.length === 0}
      emptyState={{
        title: 'No students added yet',
        description: 'Add students to start tracking enrollment, classes, and parent information.',
        actionLabel: onAddStudent ? 'Add Student' : undefined,
        onAction: onAddStudent,
        icon: 'hugeicons:student',
      }}
      pagination={pagination}
      onPageChange={onPageChange}
      skeletonColumns={5}
      variant="card"
    >
      <Table>
        <Table.Head>
          <Table.Row className="border-b-0">
            <Table.HeaderCell>Name</Table.HeaderCell>
            <Table.HeaderCell>Class</Table.HeaderCell>
            <Table.HeaderCell>Date Admitted</Table.HeaderCell>
            <Table.HeaderCell>Parent Contact</Table.HeaderCell>
            <Table.HeaderCell>Action</Table.HeaderCell>
          </Table.Row>
        </Table.Head>
        <Table.Body>
          {students.map((student) => {
            const fullName = getStudentFullName(student)

            return (
              <Table.Row key={student.id}>
                <Table.Cell variant="primary">
                  <div className="flex items-center gap-3">
                    <AvatarComponent fullName={fullName} size={40} />
                    <div className="space-y-1">
                      <p>{fullName}</p>
                      <p className="text-xs font-normal text-slate-500">{student.student_id}</p>
                    </div>
                  </div>
                </Table.Cell>
                <Table.Cell>{student.stream?.full_name ?? student.class_level?.name ?? '-'}</Table.Cell>
                <Table.Cell>{formatAdmissionDate(student.admission_date)}</Table.Cell>
                <Table.Cell>
                  <div className="space-y-1">
                    <p>{student.primary_parent?.name ?? '-'}</p>
                    <p className="text-xs text-slate-500">
                      {student.primary_parent?.phone_number ?? '-'}
                    </p>
                  </div>
                </Table.Cell>
                <Table.Cell>
                  <ActionButton
                    icon="hugeicons:view"
                    label={`View ${fullName}`}
                    onClick={() => onViewStudent?.(student)}
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

export default StudentsTable
