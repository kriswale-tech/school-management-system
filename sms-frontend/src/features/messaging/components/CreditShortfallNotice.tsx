import { Link } from 'react-router-dom'
import type { CreditCoverage } from '../types'

type CreditShortfallNoticeProps = {
  credits?: CreditCoverage | null
}

function line(label: string, balance: number, needed: number, shortfallMessages: number) {
  const noun = shortfallMessages === 1 ? 'message' : 'messages'
  return `${label} needs ${needed} credit${needed === 1 ? '' : 's'} and you have ${balance}. About ${shortfallMessages} ${noun} will be skipped.`
}

const CreditShortfallNotice = ({ credits }: CreditShortfallNoticeProps) => {
  if (!credits) return null
  const warnings = [
    credits.sms.needed > 0 && !credits.sms.sufficient
      ? line('SMS', credits.sms.balance, credits.sms.needed, credits.sms.shortfall_messages)
      : null,
    credits.email.needed > 0 && !credits.email.sufficient
      ? line(
          'Email',
          credits.email.balance,
          credits.email.needed,
          credits.email.shortfall_messages,
        )
      : null,
  ].filter(Boolean)

  if (warnings.length === 0) return null

  return (
    <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-950">
      <p className="font-medium">Credits will not cover this send.</p>
      <ul className="mt-1 list-disc space-y-1 pl-4">
        {warnings.map((warning) => (
          <li key={warning}>{warning}</li>
        ))}
      </ul>
      <Link to="/settings/messaging" className="mt-2 inline-block font-medium text-amber-950 underline">
        Buy credits
      </Link>
    </div>
  )
}

export default CreditShortfallNotice
