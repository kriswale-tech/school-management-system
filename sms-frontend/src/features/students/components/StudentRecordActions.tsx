import { useState } from 'react'
import toast from 'react-hot-toast'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import Button from '@/components/ui/Button'
import { Capability } from '@/features/auth/capabilities'
import { useAuth } from '@/features/auth/hooks'
import { useCan } from '@/features/auth/hooks/useCan'
import { getApiErrorMessage } from '@/utils'
import { clearStudentGraduation, reactivateStudent } from '../services'
import type { StudentDetail } from '../types'
import { STUDENT_DETAIL_QUERY_KEY } from '../utils'
import MarkStudentLeftModal from './MarkStudentLeftModal'

type StudentRecordActionsProps = {
  student: StudentDetail
}

const StudentRecordActions = ({ student }: StudentRecordActionsProps) => {
  const [leaveOpen, setLeaveOpen] = useState(false)
  const { user } = useAuth()
  const canMarkLeft = useCan(Capability.STUDENTS_MARK_LEFT)
  const queryClient = useQueryClient()
  const isAdmin = user?.role === 'admin'

  const { mutate: clearGraduation, isPending: clearingGraduation } = useMutation({
    mutationFn: () => clearStudentGraduation(student.id),
    onSuccess: (updated) => {
      queryClient.setQueryData([STUDENT_DETAIL_QUERY_KEY, student.id], updated)
      toast.success('Graduation cleared')
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, 'Unable to clear graduation'))
    },
  })

  const { mutate: reactivate, isPending: reactivating } = useMutation({
    mutationFn: () => reactivateStudent(student.id),
    onSuccess: (updated) => {
      queryClient.setQueryData([STUDENT_DETAIL_QUERY_KEY, student.id], updated)
      toast.success('Student reactivated')
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, 'Unable to reactivate student'))
    },
  })

  const showMarkLeft = canMarkLeft && student.is_active && !student.is_graduated
  const showReactivate = isAdmin && !student.is_active && !student.is_graduated
  const showClearGraduation = isAdmin && student.is_graduated

  if (!showMarkLeft && !showReactivate && !showClearGraduation) {
    return null
  }

  return (
    <>
      {showClearGraduation ? (
        <Button
          className="w-fit py-2 text-sm"
          variant="outline"
          loading={clearingGraduation}
          onClick={() => clearGraduation()}
        >
          Clear graduation
        </Button>
      ) : null}
      {showReactivate ? (
        <Button
          className="w-fit py-2 text-sm"
          variant="outline"
          loading={reactivating}
          onClick={() => reactivate()}
        >
          Reactivate
        </Button>
      ) : null}
      {showMarkLeft ? (
        <Button className="w-fit py-2 text-sm" color="red" onClick={() => setLeaveOpen(true)}>
          Mark as left
        </Button>
      ) : null}
      <MarkStudentLeftModal
        open={leaveOpen}
        student={student}
        onClose={() => setLeaveOpen(false)}
      />
    </>
  )
}

export default StudentRecordActions
