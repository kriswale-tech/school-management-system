import { useState } from 'react'
import { Icon } from '@iconify/react'
import Button from '@/components/ui/Button'
import EditStaffUserModal from '../EditStaffUserModal'
import type { EditableStaffUser, StaffDeskDetail } from '../../types'
import {
  formatStaffDate,
  formatStaffGenderLabel,
  formatStaffRoleSubtitle,
  STAFF_DESK_QUERY_KEY,
} from '../../utils'

const emptyProfile = {
  profile_picture: null,
  bio: null,
  date_of_birth: null,
  gender: null,
  address: null,
  phone_number_alt: null,
}

const toEditableUser = (staff: StaffDeskDetail): EditableStaffUser => ({
  id: staff.id,
  role: staff.role,
  first_name: staff.first_name,
  last_name: staff.last_name,
  phone_number: staff.phone_number,
  email: staff.email,
  profile: staff.profile ?? emptyProfile,
})

type StaffBioProps = {
  staff: StaffDeskDetail
}

const StaffBio = ({ staff }: StaffBioProps) => {
  const [editOpen, setEditOpen] = useState(false)

  const bioFields = [
    { label: 'Full Name', value: staff.full_name },
    { label: 'Role', value: formatStaffRoleSubtitle(staff) },
    { label: 'Email', value: staff.email?.trim() || '—' },
    { label: 'Primary Contact', value: staff.phone_number },
    {
      label: 'Alternate Contact',
      value: staff.profile?.phone_number_alt?.trim() || '—',
    },
    { label: 'Gender', value: formatStaffGenderLabel(staff.profile?.gender) },
    {
      label: 'Date of Birth',
      value: formatStaffDate(staff.profile?.date_of_birth),
    },
    { label: 'Address', value: staff.profile?.address?.trim() || '—' },
    { label: 'Date Added', value: formatStaffDate(staff.date_added) },
    { label: 'Status', value: staff.is_active ? 'Active' : 'Inactive' },
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
            <span className="text-slate-800 text-right max-w-[60%]">{field.value}</span>
          </div>
        ))}
        <div className="flex items-center justify-end py-4 border-slate-300">
          <Button className="w-fit" onClick={() => setEditOpen(true)}>
            <Icon icon="hugeicons:pencil-edit-02" />
            Edit
          </Button>
        </div>
      </div>

      <EditStaffUserModal
        open={editOpen}
        user={toEditableUser(staff)}
        onClose={() => setEditOpen(false)}
        invalidateQueryKey={STAFF_DESK_QUERY_KEY}
        previewAlt="Staff profile photo preview"
      />
    </>
  )
}

export default StaffBio
