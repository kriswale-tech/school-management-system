interface StatsCardProps {
  title: string
  value: string
}
const StatsCard = ({ title, value }: StatsCardProps) => {
  return (
    <div className="bg-white p-4  border-slate-200 custom-shadow-md">
      <h3 className=" text-slate-500  mb-5">{title}</h3>
      <p className="text-2xl text-slate-900 font-semibold">{value}</p>
    </div>
  )
}

export default StatsCard
