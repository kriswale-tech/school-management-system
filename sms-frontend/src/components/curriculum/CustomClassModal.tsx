import { useState, type FormEvent } from 'react'
import { Button, FormLabel, InputField, Modal } from '@/components/ui'
import type { AddClassPayload } from './payload-types'

export interface ClassFormValues {
  name: string
  description?: string
  order?: number
}

interface CustomClassModalProps {
  open: boolean
  mode: 'add' | 'edit'
  initialValues?: Partial<ClassFormValues>
  onClose: () => void
  onSubmit: (payload: AddClassPayload) => void
}

interface ClassModalFormProps {
  mode: 'add' | 'edit'
  initialValues: ClassFormValues
  onClose: () => void
  onSubmit: (payload: AddClassPayload) => void
}

const CustomClassModal = ({
  open,
  mode,
  initialValues = {},
  onClose,
  onSubmit,
}: CustomClassModalProps) => {
  const defaults: ClassFormValues = {
    name: initialValues.name ?? '',
    description: initialValues.description ?? '',
    order: initialValues.order,
  }

  return (
    <Modal
      open={open}
      title={mode === 'add' ? 'Add Custom Class' : 'Edit Class'}
      onClose={onClose}
    >
      {open ? (
        <ClassModalForm
          key={`${mode}-${defaults.name}-${defaults.description}-${defaults.order}`}
          mode={mode}
          initialValues={defaults}
          onClose={onClose}
          onSubmit={onSubmit}
        />
      ) : null}
    </Modal>
  )
}

const ClassModalForm = ({ mode, initialValues, onClose, onSubmit }: ClassModalFormProps) => {
  const [name, setName] = useState(initialValues.name)
  const [description, setDescription] = useState(initialValues.description ?? '')
  const [order, setOrder] = useState(initialValues.order?.toString() ?? '')
  const [nameError, setNameError] = useState('')

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    const trimmed = name.trim()

    if (!trimmed) {
      setNameError('Class name is required')
      return
    }

    const parsedOrder = order.trim() ? Number(order) : undefined

    onSubmit({
      name: trimmed,
      description: description.trim() || undefined,
      order: parsedOrder !== undefined && !Number.isNaN(parsedOrder) ? parsedOrder : undefined,
    })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-1.5">
        <FormLabel label="Class name" required />
        <InputField
          value={name}
          onChange={(event) => {
            setName(event.target.value)
            if (nameError) setNameError('')
          }}
          placeholder="Enter class name"
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

      <div className="space-y-1.5">
        <FormLabel label="Order" helperText="optional" />
        <InputField
          type="number"
          value={order}
          onChange={(event) => setOrder(event.target.value)}
          placeholder="Enter order"
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
