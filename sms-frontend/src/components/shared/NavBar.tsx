import { useQuery } from '@tanstack/react-query'
import { Icon } from '@iconify/react'
import { AppLogo } from '.'
import { useAuth } from '@/features/auth/hooks'
import { getAcademicYearAndTerm } from '@/features/setup/academic-year-and-term/services'
import type { TermApiKey } from '@/features/setup/academic-year-and-term/types'
import ProfileComponent from './ProfileComponent'

const TERM_LABELS: Record<TermApiKey, string> = {
  first_term: 'First Term',
  second_term: 'Second Term',
  third_term: 'Third Term',
}

const NavBar = () => {
  const { user } = useAuth()
  const activeSchool = user?.schools.find((school) => school.school_id === user.school_id)
  const schoolLogo = activeSchool?.school_logo

  const { data: session } = useQuery({
    queryKey: ['academicYearAndTerm'],
    queryFn: getAcademicYearAndTerm,
    enabled: Boolean(user?.school_id),
    staleTime: 60_000,
  })

  const schoolName = activeSchool?.school_name
  const termName =
    session?.terms.find((term) => term.is_active)?.name ??
    (session?.current_term ? TERM_LABELS[session.current_term] : null)
  const academicYear = session?.academic_year
  const sessionLabel = [termName, academicYear].filter(Boolean).join(' • ')

  return (
    <nav className="app-shell-header flex shrink-0 items-center justify-between border-b border-slate-200 bg-white px-4 print:hidden">
      <div className="flex min-w-0 items-center gap-3">
        {schoolLogo ? (
          <img
            src={schoolLogo}
            alt={schoolName ? `${schoolName} logo` : 'School logo'}
            className="h-11 w-auto max-w-40 shrink-0 object-contain"
          />
        ) : (
          <AppLogo widthPx={60} />
        )}

        {schoolName || sessionLabel ? (
          <div className="min-w-0 leading-tight">
            {schoolName ? (
              <p className="truncate text-sm font-bold text-slate-900">{schoolName}</p>
            ) : null}
            {sessionLabel ? (
              <p className="truncate text-xs text-slate-500">{sessionLabel}</p>
            ) : null}
          </div>
        ) : null}
      </div>

      {/* Notification and Profile */}
      <div className="flex items-center ">
        <div className="flex items-center justify-center bg-slate-100 rounded-full p-2">
          <Icon icon="hugeicons:notification-01" className="text-xl" />
        </div>
        <ProfileComponent />
      </div>
    </nav>
  )
}

export default NavBar
