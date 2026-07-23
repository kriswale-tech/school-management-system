import { Icon } from '@iconify/react'
import { mergeClasses } from '@/utils/tailwind-merge'

interface TabComponentProps {
  tabs: {
    label: string
    icon?: string
    onClick: () => void
  }[]
  activeTab: string
}
const TabComponent = ({ tabs, activeTab }: TabComponentProps) => {
  return (
    <div className="flex items-center gap-4 border-b border-slate-200">
      {tabs.map((tab) => (
        <button
          key={tab.label}
          onClick={tab.onClick}
          className={mergeClasses(
            'flex items-center gap-2 py-2 px-4 border-b-2 hover:text-slate-700 text-slate-500 cursor-pointer',
            activeTab === tab.label ? 'border-blue-400 text-slate-700' : 'border-transparent',
          )}
        >
          {tab.icon && <Icon icon={tab.icon} className="size-4" />}
          {tab.label}
        </button>
      ))}
    </div>
  )
}

export default TabComponent
