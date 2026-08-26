import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { Icon } from '@iconify/react'
import { useQuery } from '@tanstack/react-query'
import ActionBar from '@/components/shared/ActionBar'
import { ConfirmDialog, TabComponent } from '@/components/shared'
import { AvatarComponent, Button } from '@/components/ui'
import DotComponent from '@/components/ui/DotComponent'
import { getApiErrorMessage } from '@/utils'
import StaffBio from '../components/detail-pages/Bio'
import TeacherWorkspace from '../components/detail-pages/Workspace'
import { getStaffDeskDetail } from '../services'
import { DEFAULT_PROFILE_IMAGE, STAFF_DESK_QUERY_KEY } from '../utils'

const TAB_BIO = 'Bio'
const TAB_WORKSPACE = 'Workspace'

const StaffDetails = () => {
  const { id } = useParams<{ id: string }>()
  const [activeTab, setActiveTab] = useState(TAB_BIO)
  const [deactivateOpen, setDeactivateOpen] = useState(false)

  const {
    data: staff,
    isLoading,
    isError,
    error,
  } = useQuery({
    queryKey: [STAFF_DESK_QUERY_KEY, 'detail', id],
    queryFn: () => getStaffDeskDetail(id!),
    enabled: Boolean(id),
  })

  const isTeacher = staff?.role === 'teacher'

  const tabs = [
    {
      label: TAB_BIO,
      onClick: () => setActiveTab(TAB_BIO),
    },
    ...(isTeacher
      ? [
          {
            label: TAB_WORKSPACE,
            onClick: () => setActiveTab(TAB_WORKSPACE),
          },
        ]
      : []),
  ]

  const teacherSubtypeLabel =
    staff && isTeacher
      ? [
          staff.is_subject_teacher ? 'Subject Teacher' : null,
          staff.is_class_teacher ? 'Class Teacher' : null,
        ]
          .filter(Boolean)
          .join(' • ')
      : ''

  return (
    <div className="space-y-6">
      <ActionBar back title="Staff Details" />

      <div className="bg-white p-4 custom-shadow-md">
        {isLoading ? (
          <p className="text-sm text-slate-500 py-8">Loading staff details…</p>
        ) : isError || !staff ? (
          <p className="text-sm text-red-600 py-8" role="alert">
            {getApiErrorMessage(error, 'Unable to load staff details.')}
          </p>
        ) : (
          <>
            <div className="flex flex-wrap items-start justify-between gap-4 mb-6">
              <div className="flex items-center gap-4">
                <AvatarComponent
                  image={staff.profile_picture ?? DEFAULT_PROFILE_IMAGE}
                  fullName={staff.full_name}
                  size={100}
                />
                <div>
                  <h2 className="text-2xl font-medium mb-1">{staff.full_name}</h2>
                  {teacherSubtypeLabel ? (
                    <span className="text-sm text-gray-500">{teacherSubtypeLabel}</span>
                  ) : (
                    <span className="text-sm text-gray-500 capitalize">{staff.role}</span>
                  )}
                  <DotComponent />
                  <span
                    className={
                      staff.is_active ? 'text-sm text-green-600' : 'text-sm text-slate-500'
                    }
                  >
                    {staff.is_active ? 'Active' : 'Inactive'}
                  </span>
                </div>
              </div>
              {staff.is_active ? (
                <Button
                  type="button"
                  variant="ghost"
                  color="red"
                  className="py-2 text-sm max-w-fit shrink-0"
                  onClick={() => setDeactivateOpen(true)}
                >
                  <Icon icon="hugeicons:unavailable" className="size-4" />
                  Deactivate
                </Button>
              ) : null}
            </div>

            <TabComponent tabs={tabs} activeTab={activeTab} />

            <div className="mt-4">
              {activeTab === TAB_BIO && <StaffBio staff={staff} />}
              {activeTab === TAB_WORKSPACE && isTeacher ? (
                <TeacherWorkspace staff={staff} />
              ) : null}
            </div>

            <ConfirmDialog
              open={deactivateOpen}
              title="Deactivate staff"
              message={`Deactivate ${staff.full_name}? They will no longer have access to this school until reactivated.`}
              confirmLabel="Deactivate"
              onClose={() => setDeactivateOpen(false)}
              onConfirm={() => {
                // Endpoint wiring comes later — UI confirmation only for now.
                setDeactivateOpen(false)
              }}
            />
          </>
        )}
      </div>
    </div>
  )
}

export default StaffDetails
