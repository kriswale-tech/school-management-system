import toast from 'react-hot-toast'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { ConfirmDialog, Table, TableWrapper } from '@/components/shared'
import ActionButton from '@/components/ui/ActionButton'
import AvatarComponent from '@/components/ui/AvatarComponent'
import { deleteStaff } from '@/features/staff/services'
import type { PaginatedResponse } from '@/types/generalTypes'
import { getApiErrorMessage } from '@/utils'
import type { Teacher } from '../types'
import {
  formatClassTeacherAssignmentsLabel,
  formatTeachingAssignmentsLabel,
  getTeacherProfileImage,
} from '../utils'
import EditTeacherModal from './EditTeacherModal'
import AssignTeacherModal from './AssignTeacherModal'

type TeacherTableProps = {
  teachers: Teacher[]
  isLoading?: boolean
  pagination?: PaginatedResponse<Teacher> | null
  onPageChange?: (page: number) => void
  onAddTeacher?: () => void
}

const deleteButtonClassName = 'text-red-600 hover:bg-red-50 hover:text-red-700'

const TeacherTable = ({
  teachers,
  isLoading = false,
  pagination = null,
  onPageChange,
  onAddTeacher,
}: TeacherTableProps) => {
  const queryClient = useQueryClient()
  const [editingTeacher, setEditingTeacher] = useState<Teacher | null>(null)
  const [assigningTeacherId, setAssigningTeacherId] = useState<string | null>(null)
  const [deletingTeacher, setDeletingTeacher] = useState<Teacher | null>(null)

  const assigningTeacher = teachers.find((teacher) => teacher.id === assigningTeacherId) ?? null

  const { mutate: removeTeacher, isPending: isDeleting } = useMutation({
    mutationFn: deleteStaff,
    onSuccess: () => {
      toast.success('Teacher deleted')
      void queryClient.invalidateQueries({ queryKey: ['teachers'] })
      setDeletingTeacher(null)
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, 'Unable to delete teacher'))
    },
  })

  return (
    <>
      <TableWrapper
        variant="form-field"
        isLoading={isLoading}
        isEmpty={!isLoading && teachers.length === 0}
        emptyState={{
          title: 'No teachers added yet',
          description:
            'Start building your teaching staff by adding teachers. You can assign subjects, classes, and access permissions after creation.',
          actionLabel: 'Add Teacher',
          onAction: onAddTeacher ?? (() => {}),
          image: '/icons/add-teacher.svg',
        }}
        pagination={pagination}
        onPageChange={onPageChange}
        skeletonColumns={4}
      >
        <Table>
          <Table.Head>
            <Table.Row className="border-b-0">
              <Table.HeaderCell>Teacher Name</Table.HeaderCell>
              <Table.HeaderCell>Contact</Table.HeaderCell>
              <Table.HeaderCell>Assigned Subject(s)</Table.HeaderCell>
              <Table.HeaderCell>Actions</Table.HeaderCell>
            </Table.Row>
          </Table.Head>
          <Table.Body>
            {teachers.map((teacher) => (
              <Table.Row key={teacher.id}>
                <Table.Cell variant="primary">
                  <div className="flex items-center gap-3">
                    <AvatarComponent
                      image={getTeacherProfileImage(teacher)}
                      fullName={teacher.full_name}
                      size={40}
                    />
                    <div className="space-y-1">
                      <p>{teacher.full_name}</p>
                      <p className="text-xs font-normal text-slate-500">
                        {formatClassTeacherAssignmentsLabel(teacher.class_teacher_assignments)}
                      </p>
                    </div>
                  </div>
                </Table.Cell>
                <Table.Cell>
                  <div className="space-y-1">
                    <p>{teacher.phone_number}</p>
                    <p className="text-xs text-slate-500">{teacher.email ?? '-'}</p>
                  </div>
                </Table.Cell>
                <Table.Cell>
                  {formatTeachingAssignmentsLabel(teacher.teaching_assignments.length)}
                </Table.Cell>
                <Table.Cell>
                  <div className="flex shrink-0 items-center gap-1">
                    <ActionButton
                      icon="hugeicons:task-add-02"
                      label={`Assign ${teacher.full_name}`}
                      onClick={() => setAssigningTeacherId(teacher.id)}
                    />
                    <ActionButton
                      icon="hugeicons:edit-02"
                      label={`Edit ${teacher.full_name}`}
                      onClick={() => setEditingTeacher(teacher)}
                    />
                    <ActionButton
                      icon="hugeicons:delete-02"
                      label={`Delete ${teacher.full_name}`}
                      className={deleteButtonClassName}
                      onClick={() => setDeletingTeacher(teacher)}
                    />
                  </div>
                </Table.Cell>
              </Table.Row>
            ))}
          </Table.Body>
        </Table>
      </TableWrapper>

      <AssignTeacherModal
        open={Boolean(assigningTeacher)}
        teacher={assigningTeacher}
        onClose={() => setAssigningTeacherId(null)}
      />

      <EditTeacherModal
        open={Boolean(editingTeacher)}
        teacher={editingTeacher}
        onClose={() => setEditingTeacher(null)}
      />

      <ConfirmDialog
        open={Boolean(deletingTeacher)}
        title="Delete teacher"
        message={`Are you sure you want to delete "${deletingTeacher?.full_name}"? This action cannot be undone.`}
        confirmLabel="Delete"
        onClose={() => setDeletingTeacher(null)}
        onConfirm={() => {
          if (deletingTeacher) removeTeacher(deletingTeacher.id)
        }}
        isLoading={isDeleting}
      />
    </>
  )
}

export default TeacherTable
