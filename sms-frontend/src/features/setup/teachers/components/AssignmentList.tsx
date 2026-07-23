import ActionButton from '@/components/ui/ActionButton'

type AssignmentListProps = {
  title: string
  emptyMessage: string
  items: { id: string; label: string }[]
  onRemove: (id: string) => void
}

const AssignmentList = ({ title, emptyMessage, items, onRemove }: AssignmentListProps) => {
  return (
    <div className="space-y-2">
      <p className="text-sm font-medium text-slate-900">{title}</p>
      {items.length === 0 ? (
        <p className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-3 text-sm text-slate-500">
          {emptyMessage}
        </p>
      ) : (
        <ul className="space-y-2">
          {items.map((item) => (
            <li
              key={item.id}
              className="flex items-center justify-between gap-3 rounded-lg border border-slate-200 bg-white px-3 py-2"
            >
              <span className="text-sm text-slate-700">{item.label}</span>
              <ActionButton
                icon="hugeicons:delete-02"
                label={`Remove ${item.label}`}
                className="text-red-600 hover:bg-red-50 hover:text-red-700"
                onClick={() => onRemove(item.id)}
              />
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

export default AssignmentList
