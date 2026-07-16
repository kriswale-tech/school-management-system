import { useState, type FormEvent } from 'react'
import { Button, FormLabel, InputField, Modal } from '@/components/ui'
import type { AddStreamPayload } from '../class-subject-setup-types'

interface StreamModalProps {
  open: boolean
  mode: 'add' | 'edit'
  initialValues?: Partial<AddStreamPayload>
  onClose: () => void
  onSubmit: (payload: AddStreamPayload) => void
}

interface StreamModalFormProps {
  mode: 'add' | 'edit'
  initialValues: AddStreamPayload
  onClose: () => void
  onSubmit: (payload: AddStreamPayload) => void
}

const StreamModal = ({
  open,
  mode,
  initialValues = {},
  onClose,
  onSubmit,
}: StreamModalProps) => {
  const defaults: AddStreamPayload = {
    name: initialValues.name ?? '',
    description: initialValues.description ?? '',
  }

  return (
    <Modal open={open} title={mode === 'add' ? 'Add Stream' : 'Edit Stream'} onClose={onClose}>
      {open ? (
        <StreamModalForm
          key={`${mode}-${defaults.name}-${defaults.description}`}
          mode={mode}
          initialValues={defaults}
          onClose={onClose}
          onSubmit={onSubmit}
        />
      ) : null}
    </Modal>
  )
}

const StreamModalForm = ({ mode, initialValues, onClose, onSubmit }: StreamModalFormProps) => {
  const [name, setName] = useState(initialValues.name)
  const [description, setDescription] = useState(initialValues.description ?? '')
  const [nameError, setNameError] = useState('')

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    const trimmed = name.trim()

    if (!trimmed) {
      setNameError('Stream name is required')
      return
    }

    onSubmit({
      name: trimmed,
      description: description.trim() || undefined,
    })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-1.5">
        <FormLabel label="Stream name" required />
        <InputField
          value={name}
          onChange={(event) => {
            setName(event.target.value)
            if (nameError) setNameError('')
          }}
          placeholder="Enter stream name"
          error={nameError}
        />
      </div>

      <div className="space-y-1.5">
        <FormLabel label="Description" helperText="optional" />
        <InputField
          value={description}
          onChange={(event) => setDescription(event.target.value)}
          placeholder="Enter description"
        />
      </div>

      <div className="grid grid-cols-2 gap-3 pt-2">
        <Button type="button" variant="outline" onClick={onClose}>
          Cancel
        </Button>
        <Button type="submit" variant="solid">
          {mode === 'add' ? 'Add Stream' : 'Save Changes'}
        </Button>
      </div>
    </form>
  )
}

export default StreamModal
