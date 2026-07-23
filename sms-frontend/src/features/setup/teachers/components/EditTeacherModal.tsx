import EditStaffUserModal from '@/features/staff/components/EditStaffUserModal'
import type { Teacher } from '../types'

type EditTeacherModalProps = {
  open: boolean
  teacher: Teacher | null
  onClose: () => void
}

const EditTeacherModal = ({ open, teacher, onClose }: EditTeacherModalProps) => {
  return (
    <EditStaffUserModal
      open={open}
      user={teacher}
      onClose={onClose}
      title="Edit Teacher"
      successMessage="Teacher updated"
      invalidateQueryKey="teachers"
      previewAlt="Teacher profile photo preview"
    />
  )
}

export default EditTeacherModal
