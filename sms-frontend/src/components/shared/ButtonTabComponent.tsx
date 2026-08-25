import { mergeClasses } from '@/utils/tailwind-merge'

export type ButtonTabItem = {
  label: string
  onClick: () => void
}

type ButtonTabComponentProps = {
  tabs: ButtonTabItem[]
  activeTab: string
  className?: string
}

const ButtonTabComponent = ({ tabs, activeTab, className }: ButtonTabComponentProps) => {
  return (
    <div
      className={mergeClasses(
        'inline-flex items-center gap-1 rounded-md bg-slate-100 p-1',
        className,
      )}
      role="tablist"
    >
      {tabs.map((tab) => {
        const isActive = activeTab === tab.label

        return (
          <button
            key={tab.label}
            type="button"
            role="tab"
            aria-selected={isActive}
            onClick={tab.onClick}
            className={mergeClasses(
              'rounded-md px-3 py-1.5 text-sm font-medium transition-colors cursor-pointer',
              isActive
                ? 'bg-white text-slate-900 shadow-sm'
                : 'bg-transparent text-slate-500 hover:text-slate-700',
            )}
          >
            {tab.label}
          </button>
        )
      })}
    </div>
  )
}

export default ButtonTabComponent
