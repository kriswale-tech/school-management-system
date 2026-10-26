import { useEffect, useState } from 'react'
import { Modal, SelectField, Button, FormLabel } from '@/components/ui'
import AddStaffUserModal from './AddStaffUserModal'
import type { StaffDeskRoleOption } from '../types'
import { STAFF_DESK_ROLE_OPTIONS } from '../types'
import { formatStaffRole, STAFF_DESK_QUERY_KEY } from '../utils'

type AddStaffFromDeskModalProps = {
  open: boolean
  onClose: () => void
  /** Roles the viewer may add. Defaults to the full admin set. */
  roleOptions?: StaffDeskRoleOption[]
}

/**
 * Add flow for the staff directory. With one manageable role (e.g. staff →
 * teacher), skips the role picker and opens the form directly.
 */
const AddStaffFromDeskModal = ({
  open,
  onClose,
  roleOptions = [...STAFF_DESK_ROLE_OPTIONS],
}: AddStaffFromDeskModalProps) => {
  const singleRole = roleOptions.length === 1 ? roleOptions[0] : null
  const [role, setRole] = useState('')
  const [formOpen, setFormOpen] = useState(false)
  const [sessionKey, setSessionKey] = useState(0)

  useEffect(() => {
    if (!open) {
      setRole('')
      setFormOpen(false)
      return
    }
    if (singleRole) {
      setRole(singleRole.value)
      setSessionKey((value) => value + 1)
      setFormOpen(true)
    }
  }, [open, singleRole?.value])

  const selectedOption =
    roleOptions.find((option) => option.value === role) ?? singleRole
  const roleLabel = selectedOption?.label ?? formatStaffRole(role)

  const handleCloseAll = () => {
    setRole('')
    setFormOpen(false)
    onClose()
  }

  const handleContinue = () => {
    if (!role) return
    setSessionKey((value) => value + 1)
    setFormOpen(true)
  }

  const showRolePicker = open && !formOpen && !singleRole
  const showForm = open && formOpen && Boolean(selectedOption)

  return (
    <>
      <Modal
        open={showRolePicker}
        title="Add Staff"
        onClose={handleCloseAll}
        className="max-w-md"
      >
        <div className="space-y-6">
          <div className="space-y-2">
            <FormLabel label="Role" className="font-normal text-base" required />
            <SelectField
              options={[...roleOptions]}
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
          open={showForm}
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
