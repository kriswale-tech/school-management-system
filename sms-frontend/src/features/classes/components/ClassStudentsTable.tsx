import { Table, TableWrapper } from '@/components/shared'
import ActionButton from '@/components/ui/ActionButton'
import AvatarComponent from '@/components/ui/AvatarComponent'
import dayjs from '@/lib/dayjs'
import { useNavigate } from 'react-router-dom'
import type { ClassStudent } from '../types'

type ClassStudentsTableProps = {
  students?: ClassStudent[]
  isLoading?: boolean
}

const formatAdmissionDate = (value: string) => {
  const date = dayjs(value)
  return date.isValid() ? date.format('DD MMM YYYY') : '-'
}

const ClassStudentsTable = ({ students = [], isLoading = false }: ClassStudentsTableProps) => {
  const navigate = useNavigate()

  return (
    <TableWrapper
      isLoading={isLoading}
      isEmpty={!isLoading && students.length === 0}
      emptyState={{
        title: 'No students in this class',
        description: 'Students enrolled in this class will appear here.',
        icon: 'hugeicons:student',
      }}
      skeletonColumns={3}
      variant="form-field"
    >
      <Table>
        <Table.Head>
          <Table.Row className="border-b-0">
            <Table.HeaderCell>Student</Table.HeaderCell>
            <Table.HeaderCell>Date Admitted</Table.HeaderCell>
            <Table.HeaderCell>Action</Table.HeaderCell>
          </Table.Row>
        </Table.Head>
        <Table.Body>
          {students.map((student) => (
            <Table.Row key={student.id}>
              <Table.Cell variant="primary">
                <div className="flex items-center gap-3">
                  <AvatarComponent fullName={student.full_name} size={40} />
                  <div className="space-y-1">
                    <p>{student.full_name}</p>
                    <p className="text-xs font-normal text-slate-500">{student.student_id}</p>
                  </div>
                </div>
              </Table.Cell>
              <Table.Cell>{formatAdmissionDate(student.admission_date)}</Table.Cell>
              <Table.Cell>
                <ActionButton
                  icon="hugeicons:view"
                  label={`View ${student.full_name}`}
                  onClick={() => navigate(`/students/${student.id}`)}
                />
              </Table.Cell>
            </Table.Row>
          ))}
        </Table.Body>
      </Table>
    </TableWrapper>
  )
}

export default ClassStudentsTable
