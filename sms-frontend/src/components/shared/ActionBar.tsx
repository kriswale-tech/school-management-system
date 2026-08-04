import { Icon } from '@iconify/react'
import { useNavigate } from 'react-router-dom'

interface ActionBarProps {
  title?: string
  children?: React.ReactNode
  back?: boolean
}

const ActionBar = ({ title, children, back = false }: ActionBarProps) => {
  const navigate = useNavigate()
  const onBack = () => {
    navigate(-1)
  }

  return (
    <div className="flex items-center justify-between bg-white px-4 py-2.5  custom-shadow-sm">
      <div className="flex items-center gap-3 min-w-0">
        {back ? (
          <button
            className="text-slate-500 hover:text-slate-900 flex items-center gap-2 py-1 cursor-pointer shrink-0"
            onClick={onBack}
          >
            <Icon icon="hugeicons:arrow-left-02" className="size-5" /> <span>Back</span>
          </button>
        ) : null}
        {title ? <h1 className="text-lg font-medium text-slate-900 truncate">{title}</h1> : null}
      </div>
      {children ? <div className="flex items-center gap-2 shrink-0">{children}</div> : null}
    </div>
  )
}

export default ActionBar
