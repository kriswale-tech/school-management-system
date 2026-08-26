import { useState } from 'react'
import { Modal, SelectField, Button, FormLabel } from '@/components/ui'
import AddStaffUserModal from './AddStaffUserModal'
import { STAFF_DESK_ROLE_OPTIONS } from '../types'
import { formatStaffRole, STAFF_DESK_QUERY_KEY } from '../utils'

type AddStaffFromDeskModalProps = {
  open: boolean
  onClose: () => void
}

/**
 * Two-step add flow for the staff directory: pick a role, then reuse the
 * shared AddStaffUserModal form (same as setup teachers/staff).
 */
const AddStaffFromDeskModal = ({ open, onClose }: AddStaffFromDeskModalProps) => {
  const [role, setRole] = useState('')
  const [formOpen, setFormOpen] = useState(false)
  const [sessionKey, setSessionKey] = useState(0)

  const selectedOption = STAFF_DESK_ROLE_OPTIONS.find((option) => option.value === role)
  const roleLabel = selectedOption?.label ?? formatStaffRole(role)

  const reset = () => {
    setRole('')
    setFormOpen(false)
  }

  const handleCloseAll = () => {
    reset()
    onClose()
  }

  const handleContinue = () => {
    if (!role) return
    setSessionKey((value) => value + 1)
    setFormOpen(true)
  }

  return (
    <>
      <Modal
        open={open && !formOpen}
        title="Add Staff"
        onClose={handleCloseAll}
        className="max-w-md"
      >
        <div className="space-y-6">
          <div className="space-y-2">
            <FormLabel label="Role" className="font-normal text-base" required />
            <SelectField
              options={[...STAFF_DESK_ROLE_OPTIONS]}
              value={role}
              onChange={setRole}
              placeholder="Select a role"
            />
            <p className="text-sm text-slate-500">
              Choose the school role for this person. Teachers can later be assigned as class
              or subject teachers for the active term.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <Button type="button" variant="outline" onClick={handleCloseAll}>
              Cancel
            </Button>
            <Button type="button" onClick={handleContinue} disabled={!role}>
              Continue
            </Button>
          </div>
        </div>
      </Modal>

      {selectedOption ? (
        <AddStaffUserModal
          open={formOpen}
          onClose={handleCloseAll}
          sessionKey={sessionKey}
          role={selectedOption.value}
          title={`Add ${roleLabel}`}
          submitLabel={`Add ${roleLabel}`}
          successMessage={`${roleLabel} added`}
          invalidateQueryKey={STAFF_DESK_QUERY_KEY}
          previewAlt="Staff profile photo preview"
        />
      ) : null}
    </>
  )
}

export default AddStaffFromDeskModal
