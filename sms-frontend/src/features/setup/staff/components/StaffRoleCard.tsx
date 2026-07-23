interface StaffRoleCardProps {
  role: {
    title: string
    description: string
    value: string
    image: string
  }
  onClick: (role: { title: string; description: string; value: string; image: string }) => void
}

const StaffRoleCard = ({ role, onClick }: StaffRoleCardProps) => {
  return (
    <div
      className="p-4 bg-slate-100 rounded-3xl border border-blue-300 cursor-pointer flex gap-2 items-center hover:border-blue-400"
      onClick={() => onClick(role)}
    >
      <div className="space-y-2">
        <h3 className=" text-slate-900">{role.title}</h3>
        <p className="text-sm text-slate-500 leading-6 ">{role.description}</p>
      </div>

      {/* image */}
      <div className="flex justify-center shrink-0">
        <img src={role.image} alt={role.title} className="" />
      </div>
    </div>
  )
}

export default StaffRoleCard
