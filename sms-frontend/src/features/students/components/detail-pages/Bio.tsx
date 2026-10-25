import { useState } from 'react'
import toast from 'react-hot-toast'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Icon } from '@iconify/react'
import Button from '@/components/ui/Button'
import { Capability } from '@/features/auth/capabilities'
import { useAuth } from '@/features/auth/hooks'
import { useCan } from '@/features/auth/hooks/useCan'
import { getApiErrorMessage } from '@/utils'
import { clearStudentGraduation, reactivateStudent } from '../../services'
import type { StudentDetail, StudentLeaveReason } from '../../types'
import { formatGenderLabel, formatStudentDate, STUDENT_DETAIL_QUERY_KEY } from '../../utils'
import EditStudentBioForm from '../EditStudentBioForm'
import MarkStudentLeftModal from '../MarkStudentLeftModal'

type BioProps = {
  student: StudentDetail
}

const LEAVE_LABELS: Record<StudentLeaveReason, string> = {
  dropout: 'Dropped out',
  transfer: 'Transferred',
  other: 'Other',
}

const statusLabel = (student: StudentDetail) => {
  if (student.is_graduated) return 'Graduated'
  if (!student.is_active) {
    const reason = student.leave_reason ? LEAVE_LABELS[student.leave_reason] : 'Left'
    return `Left · ${reason}`
  }
  return 'Active'
}

const Bio = ({ student }: BioProps) => {
  const [editOpen, setEditOpen] = useState(false)
  const [leaveOpen, setLeaveOpen] = useState(false)
  const { user } = useAuth()
  const canMarkLeft = useCan(Capability.STUDENTS_MARK_LEFT)
  const queryClient = useQueryClient()

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

  const bioFields = [
    { label: 'Full Name', value: student.full_name },
    { label: 'Student ID', value: `#${student.student_id}` },
    { label: 'Gender', value: formatGenderLabel(student.gender) },
    { label: 'Date of Birth', value: formatStudentDate(student.date_of_birth) },
    { label: 'Admission Date', value: formatStudentDate(student.admission_date) },
    { label: 'Address', value: student.address?.trim() || '—' },
    {
      label: 'Class',
      value: student.class_assignment?.display_name ?? '—',
    },
    { label: 'Status', value: statusLabel(student) },
  ]

  if (!student.is_active && student.left_at) {
    bioFields.push({
      label: 'Left on',
      value: formatStudentDate(student.left_at.slice(0, 10)),
    })
    if (student.left_by_name) {
      bioFields.push({ label: 'Marked left by', value: student.left_by_name })
    }
    if (student.leave_notes?.trim()) {
      bioFields.push({ label: 'Leave notes', value: student.leave_notes.trim() })
    }
  }

  const showMarkLeft = canMarkLeft && student.is_active && !student.is_graduated
  const showReactivate = user?.role === 'admin' && !student.is_active && !student.is_graduated

  return (
    <>
      <div className="bg-gray-100 rounded-md px-4 w-full">
        {bioFields.map((field) => (
          <div
            key={field.label}
            className="flex items-center justify-between gap-4 py-4 border-b border-slate-300"
          >
            <span className="shrink-0 text-slate-500">{field.label}</span>
            <span className="text-right text-slate-800">{field.value}</span>
          </div>
        ))}
        <div className="flex flex-wrap items-center justify-end gap-3 py-4 border-slate-300">
          {student.is_graduated && user?.role === 'admin' ? (
            <Button
              className="w-fit"
              variant="outline"
              loading={clearingGraduation}
              onClick={() => clearGraduation()}
            >
              Clear graduation
            </Button>
          ) : null}
          {showReactivate ? (
            <Button
              className="w-fit"
              variant="outline"
              loading={reactivating}
              onClick={() => reactivate()}
            >
              Reactivate
            </Button>
          ) : null}
          {showMarkLeft ? (
            <Button className="w-fit" color="red" onClick={() => setLeaveOpen(true)}>
              Mark as left
            </Button>
          ) : null}
          <Button className="w-fit" onClick={() => setEditOpen(true)}>
            <Icon icon="hugeicons:pencil-edit-02" />
            Edit
          </Button>
        </div>
      </div>

      <EditStudentBioForm
        open={editOpen}
        student={student}
        onClose={() => setEditOpen(false)}
      />
      <MarkStudentLeftModal
        open={leaveOpen}
        student={student}
        onClose={() => setLeaveOpen(false)}
      />
    </>
  )
}

export default Bio
