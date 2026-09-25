import { Icon } from '@iconify/react'
import { useNavigate } from 'react-router-dom'
import type { AdminDashboardNeedsAttentionItem } from '../types'

type NeedsAttentionCardProps = {
  items: AdminDashboardNeedsAttentionItem[]
}

const NeedsAttentionCard = ({ items }: NeedsAttentionCardProps) => {
  const navigate = useNavigate()

  return (
    <div className="bg-white p-4 custom-shadow-md flex flex-col max-h-80">
      <h3 className="text-sm font-medium text-slate-800 mb-4 shrink-0">Needs Attention</h3>

      <div className="min-h-0 flex-1 overflow-y-auto">
        {items.length === 0 ? (
          <p className="text-sm text-slate-500 py-6 text-center">Nothing needs attention right now.</p>
        ) : (
          <ul className="space-y-2">
            {items.map((item) => (
              <li key={item.code}>
                <button
                  type="button"
                  onClick={() => navigate(item.href)}
                  className="w-full flex cursor-pointer items-center justify-between gap-3 rounded-lg bg-rose-50 px-3 py-3 text-left text-sm text-rose-700 transition-colors hover:bg-rose-100 hover:shadow-sm"
                >
                  <span className="min-w-0">{item.label}</span>
                  <Icon icon="hugeicons:arrow-right-01" className="size-4 shrink-0" />
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}

export default NeedsAttentionCard
