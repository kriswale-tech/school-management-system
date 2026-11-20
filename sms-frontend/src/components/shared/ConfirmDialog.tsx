import { Button, Modal } from '@/components/ui'

interface ConfirmDialogProps {
  open: boolean
  title: string
  message: string
  confirmLabel?: string
  confirmColor?: 'slate' | 'red'
  onClose: () => void
  onConfirm: () => void
  isLoading?: boolean
}

const ConfirmDialog = ({
  open,
  title,
  message,
  confirmLabel = 'Delete',
  confirmColor = 'red',
  onClose,
  onConfirm,
  isLoading = false,
}: ConfirmDialogProps) => {
  return (
    <Modal open={open} title={title} onClose={onClose}>
      <div className="space-y-4">
        <p className="text-sm leading-relaxed text-slate-600">{message}</p>
        <div className="grid grid-cols-2 gap-3">
          <Button type="button" variant="outline" onClick={onClose} disabled={isLoading}>
            Cancel
          </Button>
          <Button type="button" color={confirmColor} onClick={onConfirm} loading={isLoading}>
            {confirmLabel}
          </Button>
        </div>
      </div>
    </Modal>
  )
}

export default ConfirmDialog
