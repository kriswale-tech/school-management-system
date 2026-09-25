import type { OverviewMetric } from '../types'

type OverviewCardProps = {
  title: string
  metrics: OverviewMetric[]
}

const OverviewCard = ({ title, metrics }: OverviewCardProps) => {
  return (
    <div className="bg-white p-4 custom-shadow-md">
      <h3 className="text-xl font-semibold text-slate-800 mb-4">{title}</h3>
      <div className="grid grid-cols-3">
        {metrics.map((metric, index) => (
          <div
            key={metric.label}
            className={`min-w-0 ${index > 0 ? 'border-l border-slate-200 pl-3' : 'pr-3'}`}
          >
            <p className="text-xs text-slate-500 leading-snug">{metric.label}</p>
            <p className="mt-1 text-xl font-semibold text-slate-900 truncate">{metric.value}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

export default OverviewCard
