import { useState, type FormEvent } from 'react'
import { Button, FormLabel, InputField, Modal } from '@/components/ui'

interface SubjectGroupModalProps {
  open: boolean
  mode: 'add' | 'edit'
  initialName?: string
  onClose: () => void
  onSubmit: (payload: { name: string }) => void
}

interface SubjectGroupModalFormProps {
  mode: 'add' | 'edit'
  initialName: string
  onClose: () => void
  onSubmit: (payload: { name: string }) => void
}

const SubjectGroupModal = ({
  open,
  mode,
  initialName = '',
  onClose,
  onSubmit,
}: SubjectGroupModalProps) => {
  return (
    <Modal open={open} title={mode === 'add' ? 'Add Group' : 'Edit Group'} onClose={onClose}>
      {open ? (
        <SubjectGroupModalForm
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

const SubjectGroupModalForm = ({
  mode,
  initialName,
  onClose,
  onSubmit,
}: SubjectGroupModalFormProps) => {
  const [name, setName] = useState(initialName)
  const [error, setError] = useState('')

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    const trimmed = name.trim()

    if (!trimmed) {
      setError('Group name is required')
      return
    }

    onSubmit({ name: trimmed })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-1.5">
        <FormLabel label="Group name" required />
        <InputField
          value={name}
          onChange={(event) => {
            setName(event.target.value)
            if (error) setError('')
          }}
          placeholder="Enter group name"
          error={error}
        />
      </div>

      <div className="grid grid-cols-2 gap-3 pt-2">
        <Button type="button" variant="outline" onClick={onClose}>
          Cancel
        </Button>
        <Button type="submit" variant="solid">
          {mode === 'add' ? 'Add Group' : 'Save Changes'}
        </Button>
      </div>
    </form>
  )
}

export default SubjectGroupModal
