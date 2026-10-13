import type { ReactNode } from 'react'

type SettingsSectionProps = {
  title: string
  description: string
  children: ReactNode
}

const SettingsSection = ({ title, description, children }: SettingsSectionProps) => {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg text-slate-900">{title}</h2>
        <p className="mt-1 text-sm text-slate-500">{description}</p>
      </div>
      {children}
    </div>
  )
}

export default SettingsSection
