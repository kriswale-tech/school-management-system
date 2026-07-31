import { useState } from 'react'
import StaffRoleCard from '@/features/setup/staff/components/StaffRoleCard'
import BulkUploadStudents from './student-bulkupload/BulkUpload'
import StudentForm from './student-form/StudentForm'
import { Icon } from '@iconify/react'

const StudentOnboarding = () => {
  const [selectedMethod, setSelectedMethod] = useState<'file-upload' | 'manual-form' | null>(null)

  const handleMethodClick = (role: {
    title: string
    description: string
    value: string
    image: string
  }) => {
    setSelectedMethod(role.value as 'file-upload' | 'manual-form')
  }

  if (selectedMethod === 'file-upload') {
    return (
      <div className="space-y-6 ">
        <CancelButton onClick={() => setSelectedMethod(null)} />
        <BulkUploadStudents />
      </div>
    )
  }

  if (selectedMethod === 'manual-form') {
    return (
      <div className="space-y-6">
        <CancelButton onClick={() => setSelectedMethod(null)} />
        <StudentForm />
      </div>
    )
  }

  return (
    <div className="space-y-6 py-4">
      <h2 className="text-sm text-slate-500">
        Select a method to begin adding your students to the system
      </h2>

      <StaffRoleCard
        role={{
          title: 'File Upload',
          description:
            'Upload many students at once using a CSV or Excel file. Perfect for large lists.',
          value: 'file-upload',
          image: '/icons/staff.svg',
        }}
        onClick={handleMethodClick}
      />
      <StaffRoleCard
        role={{
          title: 'Manual Form',
          description:
            'Add students one by one via the form. Ideal for a few entries or detailed info.',
          value: 'manual-form',
          image: '/icons/accountant.svg',
        }}
        onClick={handleMethodClick}
      />
    </div>
  )
}

export default StudentOnboarding

const CancelButton = ({ onClick }: { onClick: () => void }) => {
  return (
    <button
      className="flex justify-start items-center gap-2 text-slate-500 text-sm cursor-pointer hover:text-slate-700"
      onClick={onClick}
    >
      <Icon icon="hugeicons:arrow-left-02" className="size-4" />
      <span>Cancel</span>
    </button>
  )
}
