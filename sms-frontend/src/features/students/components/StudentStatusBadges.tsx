import { formatLeaveReason } from '../utils'

type StudentStatusBadgesProps = {
  isGraduated?: boolean
  isActive?: boolean
  leaveReason?: string | null
  isNewStudent?: boolean | null
  size?: 'sm' | 'md'
}

const pillClass = {
  sm: 'inline-flex rounded-full px-2 py-0.5 text-[11px] font-medium',
  md: 'inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium',
}

const StudentStatusBadges = ({
  isGraduated = false,
  isActive = true,
  leaveReason,
  isNewStudent = false,
  size = 'sm',
}: StudentStatusBadgesProps) => {
  const leaveLabel = formatLeaveReason(leaveReason)
  const leftText = leaveLabel ? `Left · ${leaveLabel}` : 'Left'
  const pill = pillClass[size]

  return (
    <>
      {isNewStudent ? (
        <span className={`${pill} bg-sky-100 text-sky-800`}>New student</span>
      ) : null}
      {isGraduated ? (
        <span className={`${pill} bg-violet-100 text-violet-800`}>Graduated</span>
      ) : null}
      {!isGraduated && !isActive ? (
        <span className={`${pill} bg-rose-100 text-rose-800`}>{leftText}</span>
      ) : null}
    </>
  )
}

export default StudentStatusBadges
