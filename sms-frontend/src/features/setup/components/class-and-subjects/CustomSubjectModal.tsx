import { useState, type FormEvent } from 'react'
import { Button, CheckboxField, FormLabel, InputField, Modal } from '@/components/ui'
import type { ClassForSetup, SubjectScope } from '../../types/types'

export interface SubjectFormValues {
  name: string
  classIds: string[]
}

interface CustomSubjectModalProps {
  open: boolean
  mode: 'add' | 'edit'
  subjectScope: SubjectScope
  classes: ClassForSetup[]
  initialValues?: Partial<SubjectFormValues>
  onClose: () => void
  onSubmit: (data: SubjectFormValues) => void
}

interface SubjectModalFormProps {
  mode: 'add' | 'edit'
  subjectScope: SubjectScope
  classes: ClassForSetup[]
  initialValues: SubjectFormValues
  onClose: () => void
  onSubmit: (data: SubjectFormValues) => void
}

const getClassKey = (classItem: ClassForSetup) => classItem.id ?? classItem.name

const CustomSubjectModal = ({
  open,
  mode,
  subjectScope,
  classes,
  initialValues = {},
  onClose,
  onSubmit,
}: CustomSubjectModalProps) => {
  const defaults: SubjectFormValues = {
    name: initialValues.name ?? '',
    classIds: initialValues.classIds ?? [],
  }

  return (
    <Modal
      open={open}
      title={mode === 'add' ? 'Add Custom Subject' : 'Edit Subject'}
      onClose={onClose}
    >
      {open ? (
        <SubjectModalForm
          key={`${mode}-${defaults.name}-${defaults.classIds.join(',')}`}
          mode={mode}
          subjectScope={subjectScope}
          classes={classes}
          initialValues={defaults}
          onClose={onClose}
          onSubmit={onSubmit}
        />
      ) : null}
    </Modal>
  )
}

const SubjectModalForm = ({
  mode,
  subjectScope,
  classes,
  initialValues,
  onClose,
  onSubmit,
}: SubjectModalFormProps) => {
  const [name, setName] = useState(initialValues.name)
  const [selectedClassIds, setSelectedClassIds] = useState<string[]>(initialValues.classIds)
  const [nameError, setNameError] = useState('')
  const [classesError, setClassesError] = useState('')

  const toggleClass = (classId: string) => {
    setSelectedClassIds((current) =>
      current.includes(classId) ? current.filter((id) => id !== classId) : [...current, classId],
    )
    if (classesError) setClassesError('')
  }

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault()
    const trimmed = name.trim()
    let hasError = false

    if (!trimmed) {
      setNameError('Subject name is required')
      hasError = true
    }

    if (subjectScope === 'class' && selectedClassIds.length === 0) {
      setClassesError('Select at least one class')
      hasError = true
    }

    if (hasError) return

    onSubmit({
      name: trimmed,
      classIds: subjectScope === 'class' ? selectedClassIds : [],
    })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="space-y-1.5">
        <FormLabel label="Subject name" required />
        <InputField
          value={name}
          onChange={(event) => {
            setName(event.target.value)
            if (nameError) setNameError('')
          }}
          placeholder="Enter subject name"
          error={nameError}
        />
      </div>

      {subjectScope === 'class' && (
        <div className="space-y-1.5">
          <FormLabel label="Associate with classes" required />
          <div className="max-h-48 space-y-2 overflow-y-auto rounded-lg border border-slate-300 bg-slate-50 p-3">
            {classes.map((classItem) => {
              const classKey = getClassKey(classItem)
              return (
                <CheckboxField
                  key={classKey}
                  checked={selectedClassIds.includes(classKey)}
                  onChange={() => toggleClass(classKey)}
                >
                  {classItem.name}
                </CheckboxField>
              )
            })}
          </div>
          {classesError ? <p className="text-sm text-red-600">{classesError}</p> : null}
        </div>
      )}

      {subjectScope === 'level' && (
        <p className="text-sm text-slate-500">
          This subject will be associated with all classes in this level.
        </p>
      )}

      <div className="grid grid-cols-2 gap-3 pt-2">
        <Button type="button" variant="outline" onClick={onClose}>
          Cancel
        </Button>
        <Button type="submit" variant="solid">
          {mode === 'add' ? 'Add Subject' : 'Save Changes'}
        </Button>
      </div>
    </form>
  )
}

export default CustomSubjectModal
