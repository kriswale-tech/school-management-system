import { useState } from 'react'
import { Icon } from '@iconify/react'
import { FormWrapper } from '@/features/auth/components'
import { AppLogo } from '@/components/shared'
import { AvatarComponent, LoadingSpinner } from '@/components/ui'
import type { SchoolMembership } from '@/features/auth/types'
import { mergeClasses } from '@/utils'

export interface SelectSchoolFormProps {
  schools: SchoolMembership[]
  activeSchoolId?: string | null
  onSelect: (_schoolId: string) => void
  isSubmitting?: boolean
  title?: string
  description?: string
}

const formatRole = (role: string) => role.replace(/_/g, ' ')

const SelectSchoolForm = ({
  schools,
  activeSchoolId = null,
  onSelect,
  isSubmitting = false,
  title = 'Select a school',
  description = 'You belong to more than one school. Choose which one to continue with.',
}: SelectSchoolFormProps) => {
  const [pendingSchoolId, setPendingSchoolId] = useState<string | null>(null)

  const handleSelect = (schoolId: string) => {
    if (isSubmitting) return
    setPendingSchoolId(schoolId)
    onSelect(schoolId)
  }

  return (
    <FormWrapper>
      <div className="flex justify-center items-center gap-8 flex-col text-center mb-8">
        <AppLogo />
        <div>
          <h2 className="font-semibold text-2xl mb-3">{title}</h2>
          <p className="text-lg text-slate-400">{description}</p>
        </div>
      </div>

      <ul className="space-y-3" role="list">
        {schools.map((school) => {
          const isActive = school.school_id === activeSchoolId
          const isPending = isSubmitting && pendingSchoolId === school.school_id

          return (
            <li key={school.id}>
              <button
                type="button"
                disabled={isSubmitting}
                onClick={() => handleSelect(school.school_id)}
                className={mergeClasses(
                  'flex w-full items-center gap-4 rounded-2xl border px-4 py-4 text-left transition-colors',
                  'border-slate-200 bg-white enabled:hover:border-slate-900 enabled:hover:bg-slate-50',
                  'disabled:cursor-not-allowed disabled:opacity-60',
                  isActive && 'border-slate-900 bg-slate-50',
                )}
              >
                <AvatarComponent
                  image={school.school_logo}
                  fullName={school.school_name}
                  size={48}
                  icon="hugeicons:school"
                />

                <div className="min-w-0 flex-1">
                  <p className="truncate text-base font-semibold text-slate-900">
                    {school.school_name}
                  </p>
                  <p className="mt-0.5 text-sm capitalize text-slate-500">
                    {formatRole(school.role)}
                    {isActive ? ' · Current' : ''}
                  </p>
                </div>

                {isPending ? (
                  <LoadingSpinner size={18} className="text-slate-700" />
                ) : (
                  <Icon icon="mdi:chevron-right" className="shrink-0 text-2xl text-slate-400" />
                )}
              </button>
            </li>
          )
        })}
      </ul>
    </FormWrapper>
  )
}

export default SelectSchoolForm
