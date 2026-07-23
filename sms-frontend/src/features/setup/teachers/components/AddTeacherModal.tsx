import AddStaffUserModal from '@/features/staff/components/AddStaffUserModal'

type AddTeacherModalProps = {
  open: boolean
  onClose: () => void
  sessionKey: number
}

const AddTeacherModal = ({ open, onClose, sessionKey }: AddTeacherModalProps) => {
  return (
    <AddStaffUserModal
      open={open}
      onClose={onClose}
      sessionKey={sessionKey}
      role="teacher"
      title="Add Teacher"
      submitLabel="Add Teacher"
      successMessage="Teacher added"
      invalidateQueryKey="teachers"
      previewAlt="Teacher profile photo preview"
    />
  )
}

export default AddTeacherModal
