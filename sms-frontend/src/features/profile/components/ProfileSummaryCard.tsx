import { Link } from 'react-router-dom'
import { Icon } from '@iconify/react'
import AvatarComponent from '@/components/ui/AvatarComponent'
import type { User } from '@/features/auth/types'
import { formatLastActive, formatRoleLabel } from '../utils'

type ProfileSummaryCardProps = {
  user: User
}

const ProfileSummaryCard = ({ user }: ProfileSummaryCardProps) => {
  const activeSchool = user.schools.find((school) => school.school_id === user.school_id)
  const otherSchools = user.schools.filter((school) => school.school_id !== user.school_id)

  return (
    <div className="space-y-6">
      <div className="flex flex-col items-center text-center sm:flex-row sm:items-start sm:text-left sm:gap-4">
        <AvatarComponent
          image={user.profile?.profile_picture}
          fullName={user.full_name}
          size={88}
          className="shrink-0"
        />
        <div className="min-w-0 pt-1">
          <h2 className="text-lg text-slate-900">{user.full_name}</h2>
          <p className="mt-1 text-sm text-slate-500">{formatRoleLabel(user.role)}</p>
          {activeSchool ? (
            <p className="mt-2 text-sm font-medium text-slate-700">{activeSchool.school_name}</p>
          ) : null}
        </div>
      </div>

      <dl className="divide-y divide-slate-200 rounded-lg border border-slate-200">
        <div className="flex items-start justify-between gap-4 px-4 py-3">
          <dt className="text-sm text-slate-500">Login phone</dt>
          <dd className="text-sm text-slate-900 text-right">{user.phone_number}</dd>
        </div>
        <div className="flex items-start justify-between gap-4 px-4 py-3">
          <dt className="text-sm text-slate-500">Last active here</dt>
          <dd className="text-sm text-slate-900 text-right">{formatLastActive(user.last_active_at)}</dd>
        </div>
      </dl>

      <p className="text-xs text-slate-500">
        Sign-in uses your login phone and a one-time code. To change that number, ask a school
        admin.
      </p>

      {otherSchools.length > 0 ? (
        <div className="space-y-2">
          <p className="text-sm font-medium text-slate-700">Other schools</p>
          <ul className="space-y-2">
            {otherSchools.map((school) => (
              <li
                key={school.id}
                className="flex items-center justify-between rounded-lg border border-slate-200 px-3 py-2 text-sm"
              >
                <span className="text-slate-800">{school.school_name}</span>
                <span className="text-slate-500">{formatRoleLabel(school.role)}</span>
              </li>
            ))}
          </ul>
          <Link
            to="/auth/select-school"
            className="inline-flex items-center gap-1 text-sm text-sky-700 hover:text-sky-800"
          >
            <Icon icon="hugeicons:school" className="size-4" />
            Switch school
          </Link>
        </div>
      ) : null}
    </div>
  )
}

export default ProfileSummaryCard
