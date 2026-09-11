import { useEffect, useState } from 'react'
import { Button, FormLabel, InputField, Modal } from '@/components/ui'
import type { CaItem } from '../assessment/types'

type AddCaItemModalProps = {
  open: boolean
  mode: 'create' | 'edit'
  initial?: CaItem | null
  onClose: () => void
  onSubmit: (_payload: { name: string; max_marks: number }) => string | null
}

const AddCaItemModal = ({ open, mode, initial, onClose, onSubmit }: AddCaItemModalProps) => {
  const [name, setName] = useState('')
  const [maxMarks, setMaxMarks] = useState('20')
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    setName(initial?.name ?? '')
    setMaxMarks(initial ? String(initial.max_marks) : '20')
    setError(null)
  }, [open, initial])

  if (!open) return null

  const title = mode === 'edit' ? 'Edit class assessment' : 'Add class assessment'

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault()
    const trimmed = name.trim()
    const max = Number(maxMarks)
    if (!trimmed) {
      setError('Enter an assessment name.')
      return
    }
    if (!Number.isFinite(max) || max <= 0) {
      setError('Max marks must be greater than 0.')
      return
    }
    const submitError = onSubmit({ name: trimmed, max_marks: max })
    if (submitError) {
      setError(submitError)
      return
    }
  }

  return (
    <Modal open={open} title={title} onClose={onClose}>
      <form className="space-y-4" onSubmit={handleSubmit}>
        <div>
          <FormLabel label="Assessment name" required />
          <InputField
            id="ca-item-name"
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="e.g. Homework 2"
            className="p-3 text-sm"
          />
        </div>
        <div>
          <FormLabel label="Highest marks" required />
          <InputField
            id="ca-item-max"
            type="number"
            min={1}
            step={1}
            value={maxMarks}
            onChange={(event) => setMaxMarks(event.target.value)}
            className="p-3 text-sm"
          />
        </div>
        {error ? (
          <p className="text-sm text-red-600" role="alert">
            {error}
          </p>
        ) : null}
        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="ghost" className="max-w-fit py-2 text-sm" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" className="max-w-fit py-2 text-sm">
            {mode === 'edit' ? 'Save changes' : 'Add assessment'}
          </Button>
        </div>
      </form>
    </Modal>
  )
}

export default AddCaItemModal
