import { useState, type FormEvent } from 'react'
import { Button, FormLabel, InputField, Modal } from '@/components/ui'

interface CustomClassModalProps {
  open: boolean
  mode: 'add' | 'edit'
  initialName?: string
  onClose: () => void
  onSubmit: (_name: string) => void
}

interface ClassModalFormProps {
  mode: 'add' | 'edit'
  initialName: string
  onClose: () => void
  onSubmit: (_name: string) => void
}

const CustomClassModal = ({
  open,
  mode,
  initialName = '',
  onClose,
  onSubmit,
}: CustomClassModalProps) => {
  return (
    <Modal
      open={open}
      title={mode === 'add' ? 'Add Custom Class' : 'Edit Class'}
      onClose={onClose}
    >
      {open ? (
        <ClassModalForm
          key={`${mode}-${initialName}`}
          mode={mode}
          initialName={initialName}
          onClose={onClose}
          onSubmit={onSubmit}
        />
      ) : null}
    </Modal>
  )
}

const ClassModalForm = ({ mode, initialName, onClose, onSubmit }: ClassModalFormProps) => {
  const [name, setName] = useState(initialName)
  const [error, setError] = useState('')

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    const trimmed = name.trim()

    if (!trimmed) {
      setError('Class name is required')
      return
    }

    onSubmit(trimmed)
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-1.5">
        <FormLabel label="Class name" required />
        <InputField
          value={name}
          onChange={(event) => {
            setName(event.target.value)
            if (error) setError('')
          }}
          placeholder="Enter class name"
          error={error}
        />
      </div>

      <div className="grid grid-cols-2 gap-3 pt-2">
        <Button type="button" variant="outline" onClick={onClose}>
          Cancel
        </Button>
        <Button type="submit" variant="solid">
          {mode === 'add' ? 'Add Class' : 'Save Changes'}
        </Button>
      </div>
    </form>
  )
}

export default CustomClassModal
