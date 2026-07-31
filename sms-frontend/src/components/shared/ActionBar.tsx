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
      {/* title */}
      {back ? (
        <button className="text-slate-900 hover:text-slate-600" onClick={onBack}>
          <Icon icon="hugeicons:arrow-left" className="w-5 h-5" />
        </button>
      ) : (
        <>
          <h1 className="text-xl font-medium text-slate-900">{title}</h1>
          {/* actions */}
          <div className="flex items-center gap-2">{children}</div>
        </>
      )}
    </div>
  )
}

export default ActionBar
