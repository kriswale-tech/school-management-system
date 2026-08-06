import toast from 'react-hot-toast'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { AvatarComponent, Button, Modal, SearchComponent } from '@/components/ui'
import { getApiErrorMessage, mergeClasses } from '@/utils'
import { assignClassTeacher, getClassTeacherOptions } from '../services'

type AssignClassTeacherProps = {
  open: boolean
  streamId: string
  classDisplayName?: string
  selectedTeacherId?: string | null
  onClose: () => void
  onAssigned?: () => void
}

const AssignClassTeacher = ({
  open,
  streamId,
  classDisplayName = 'this class',
  selectedTeacherId = null,
  onClose,
  onAssigned,
}: AssignClassTeacherProps) => {
  if (!open) return null

  return (
    <AssignClassTeacherContent
      streamId={streamId}
      classDisplayName={classDisplayName}
      selectedTeacherId={selectedTeacherId}
      onClose={onClose}
      onAssigned={onAssigned}
    />
  )
}

type AssignClassTeacherContentProps = Omit<AssignClassTeacherProps, 'open'>

const AssignClassTeacherContent = ({
  streamId,
  classDisplayName = 'this class',
  selectedTeacherId = null,
  onClose,
  onAssigned,
}: AssignClassTeacherContentProps) => {
  const [search, setSearch] = useState('')
  const [selectedId, setSelectedId] = useState<string | null>(selectedTeacherId)

  const { data, isLoading } = useQuery({
    queryKey: ['classes', 'teachers', { search }],
    queryFn: () => getClassTeacherOptions({ search: search || undefined }),
  })

  const teachers = data?.results ?? []

  const { mutate: saveAssignment, isPending } = useMutation({
    mutationFn: () =>
      assignClassTeacher(streamId, {
        teacher_id: selectedId!,
      }),
    onSuccess: () => {
      toast.success('Class teacher assigned')
      onAssigned?.()
      onClose()
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, 'Unable to assign class teacher'))
    },
  })

  const emptyMessage = useMemo(() => {
    if (isLoading) return 'Loading teachers...'
    if (search.trim()) return 'No teachers match your search.'
    return 'No teachers available yet.'
  }, [isLoading, search])

  return (
    <Modal
      open
      title="Assign Class Teacher"
      onClose={onClose}
      scrollable
      className="max-w-lg"
    >
      <div className="space-y-4">
        <p className="text-sm text-slate-500">
          Select a teacher to assign as class teacher for{' '}
          <span className="font-medium text-slate-700">{classDisplayName}</span>.
        </p>

        <SearchComponent
          value={search}
          onChange={setSearch}
          debounceMs={200}
          placeholder="Search teachers..."
          className="max-w-none"
        />

        <ul className="space-y-2">
          {teachers.length === 0 ? (
            <li className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-4 text-sm text-slate-500">
              {emptyMessage}
            </li>
          ) : (
            teachers.map((teacher) => {
              const isSelected = selectedId === teacher.id

              return (
                <li key={teacher.id}>
                  <button
                    type="button"
                    onClick={() => setSelectedId(teacher.id)}
                    className={mergeClasses(
                      'flex w-full items-start gap-3 rounded-lg border px-3 py-3 text-left transition-colors',
                      isSelected
                        ? 'border-blue-400 bg-blue-50'
                        : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50',
                    )}
                  >
                    <AvatarComponent fullName={teacher.full_name} size={40} />
                    <div className="min-w-0 space-y-1">
                      <p className="font-medium text-slate-900">{teacher.full_name}</p>
                      <p className="text-sm text-slate-500">{teacher.class_teacher_summary}</p>
                    </div>
                  </button>
                </li>
              )
            })
          )}
        </ul>

        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="outline" onClick={onClose} disabled={isPending}>
            Cancel
          </Button>
          <Button
            type="button"
            onClick={() => saveAssignment()}
            disabled={!selectedId || isPending}
            loading={isPending}
          >
            Save
          </Button>
        </div>
      </div>
    </Modal>
  )
}

export default AssignClassTeacher
