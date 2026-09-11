interface StatsCardProps {
  title: string
  value: string
  /** Optional short explanation under the value. */
  description?: string
}

const StatsCard = ({ title, value, description }: StatsCardProps) => {
  return (
    <div className="bg-white p-4 border-slate-200 custom-shadow-md">
      <h3 className="text-slate-500 mb-5">{title}</h3>
      <p className="text-2xl text-slate-900 font-semibold">{value}</p>
      {description ? (
        <p className="mt-2 text-sm text-slate-500 leading-snug">{description}</p>
      ) : null}
    </div>
  )
}

export default StatsCard
