import { useState } from 'react'
import { Icon } from '@iconify/react'
import Button from '@/components/ui/Button'
import type { StudentDetail } from '../../types'
import { formatGenderLabel, formatLeaveReason, formatStudentDate } from '../../utils'
import EditStudentBioForm from '../EditStudentBioForm'

type BioProps = {
  student: StudentDetail
}

const statusLabel = (student: StudentDetail) => {
  if (student.is_graduated) return 'Graduated'
  if (!student.is_active) {
    const reason = formatLeaveReason(student.leave_reason)
    return reason ? `Left · ${reason}` : 'Left'
  }
  return 'Active'
}

const Bio = ({ student }: BioProps) => {
  const [editOpen, setEditOpen] = useState(false)

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
    {
      label: 'Enrollment',
      value:
        student.is_new_student === true
          ? 'New student'
          : student.is_new_student === false
            ? 'Continuing student'
            : '—',
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
    </>
  )
}

export default Bio
