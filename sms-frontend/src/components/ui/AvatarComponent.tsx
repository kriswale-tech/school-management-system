import { useMemo } from 'react'
import { Icon } from '@iconify/react'
import { mergeClasses } from '@/utils'

const DEFAULT_SIZE = 40
const FALLBACK_ICON = 'hugeicons:user'

const AVATAR_COLORS = [
  'bg-sky-100 text-sky-700',
  'bg-emerald-100 text-emerald-700',
  'bg-violet-100 text-violet-700',
  'bg-amber-100 text-amber-700',
  'bg-rose-100 text-rose-700',
  'bg-cyan-100 text-cyan-700',
  'bg-indigo-100 text-indigo-700',
  'bg-teal-100 text-teal-700',
] as const

export type AvatarComponentProps = {
  image?: string | null
  fullName?: string | null
  size?: number
  className?: string
  icon?: string
}

function getInitials(fullName: string) {
  const words = fullName.trim().split(/\s+/).filter(Boolean)

  if (words.length >= 2) {
    return `${words[0][0]}${words[1][0]}`.toUpperCase()
  }

  if (words.length === 1) {
    return words[0].slice(0, 2).toUpperCase()
  }

  return ''
}

function getColorClass(seed: string) {
  let hash = 0

  for (let index = 0; index < seed.length; index += 1) {
    hash = seed.charCodeAt(index) + ((hash << 5) - hash)
  }

  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length]
}

const AvatarComponent = ({
  image,
  fullName,
  size = DEFAULT_SIZE,
  className,
  icon = FALLBACK_ICON,
}: AvatarComponentProps) => {
  const trimmedName = fullName?.trim() ?? ''
  const initials = useMemo(() => getInitials(trimmedName), [trimmedName])
  const colorClass = useMemo(() => getColorClass(trimmedName || 'avatar'), [trimmedName])

  const sharedClassName = mergeClasses(
    'inline-flex shrink-0 items-center justify-center overflow-hidden rounded-full',
    className,
  )

  const sharedStyle = { width: size, height: size }

  if (image) {
    return (
      <img
        src={image}
        alt={trimmedName || 'Avatar'}
        className={mergeClasses(sharedClassName, 'object-cover')}
        style={sharedStyle}
      />
    )
  }

  if (initials) {
    return (
      <div
        className={mergeClasses(sharedClassName, colorClass, 'font-medium uppercase')}
        style={{ ...sharedStyle, fontSize: size * 0.36 }}
        aria-label={trimmedName}
      >
        {initials}
      </div>
    )
  }

  return (
    <div
      className={mergeClasses(sharedClassName, 'bg-slate-100 text-slate-500')}
      style={sharedStyle}
      aria-label="Avatar"
    >
      <Icon icon={icon} width={size * 0.55} height={size * 0.55} />
    </div>
  )
}

export default AvatarComponent
