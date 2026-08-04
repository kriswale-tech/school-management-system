import { useState } from 'react'
import { Icon } from '@iconify/react'
import Button from '@/components/ui/Button'
import type { StudentDetail } from '../../types'
import { formatGenderLabel, formatStudentDate } from '../../utils'
import EditStudentBioForm from '../EditStudentBioForm'

type BioProps = {
  student: StudentDetail
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
    { label: 'Status', value: student.is_active ? 'Active' : 'Inactive' },
  ]

  return (
    <>
      <div className="bg-gray-100 rounded-md px-4 w-full">
        {bioFields.map((field) => (
          <div
            key={field.label}
            className="flex items-center justify-between py-4 border-b border-slate-300"
          >
            <span className="text-slate-500">{field.label}</span>
            <span className="text-slate-800">{field.value}</span>
          </div>
        ))}
        <div className="flex items-center justify-end py-4 border-slate-300">
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
