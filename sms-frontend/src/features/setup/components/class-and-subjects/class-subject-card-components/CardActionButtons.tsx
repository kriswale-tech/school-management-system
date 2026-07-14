import { Icon } from '@iconify/react'

const CardActionButtons = ({
  editLabel,
  deleteLabel,
  onEdit,
  onDelete,
}: {
  editLabel: string
  deleteLabel: string
  onEdit: () => void
  onDelete: () => void
}) => (
  <div className="flex shrink-0 items-center gap-2">
    <button
      type="button"
      title={editLabel}
      aria-label={editLabel}
      onClick={onEdit}
      className="flex size-10 items-center justify-center rounded-full border border-slate-400 text-slate-600 hover:bg-slate-50 hover:text-slate-900"
    >
      <Icon icon="hugeicons:edit-02" className="size-4" />
    </button>
    <button
      type="button"
      title={deleteLabel}
      aria-label={deleteLabel}
      onClick={onDelete}
      className="flex size-10 items-center justify-center rounded-full border border-red-400 text-red-600 hover:bg-red-50 hover:text-red-700"
    >
      <Icon icon="ic:outline-remove-circle-outline" className="size-4" />
    </button>
  </div>
)

export default CardActionButtons
