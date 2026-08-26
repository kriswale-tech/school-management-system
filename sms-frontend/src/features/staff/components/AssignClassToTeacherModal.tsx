import toast from 'react-hot-toast'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { Button, Modal, SearchComponent } from '@/components/ui'
import { assignClassTeacher, getClassList } from '@/features/classes/services'
import type { ClassListItem } from '@/features/classes/types'
import { getApiErrorMessage, mergeClasses } from '@/utils'
import { STAFF_DESK_QUERY_KEY } from '../utils'

type AssignClassToTeacherModalProps = {
  open: boolean
  teacherId: string
  teacherName: string
  onClose: () => void
}

const AssignClassToTeacherModal = ({
  open,
  teacherId,
  teacherName,
  onClose,
}: AssignClassToTeacherModalProps) => {
  if (!open) return null

  return (
    <AssignClassToTeacherModalContent
      teacherId={teacherId}
      teacherName={teacherName}
      onClose={onClose}
    />
  )
}

type ContentProps = {
  teacherId: string
  teacherName: string
  onClose: () => void
}

const AssignClassToTeacherModalContent = ({
  teacherId,
  teacherName,
  onClose,
}: ContentProps) => {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState<ClassListItem | null>(null)

  const { data, isLoading } = useQuery({
    queryKey: ['classes', 'list', { search }],
    queryFn: () => getClassList({ search: search || undefined }),
  })

  const classes = data?.results ?? []

  const { mutate: assign, isPending } = useMutation({
    mutationFn: () =>
      assignClassTeacher(selected!.id, {
        teacher_id: teacherId,
      }),
    onSuccess: () => {
      toast.success('Class assigned')
      void queryClient.invalidateQueries({ queryKey: [STAFF_DESK_QUERY_KEY] })
      void queryClient.invalidateQueries({ queryKey: ['classes'] })
      onClose()
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, 'Unable to assign class'))
    },
  })

  const emptyMessage = useMemo(() => {
    if (isLoading) return 'Loading classes…'
    if (search.trim()) return 'No classes match your search.'
    return 'No classes available for the active term.'
  }, [isLoading, search])

  return (
    <Modal open title="Assign Class" onClose={onClose} scrollable className="max-w-lg">
      <div className="space-y-4">
        <p className="text-sm text-slate-500">
          Choose a class to assign to{' '}
          <span className="font-medium text-slate-700">{teacherName}</span> as class teacher.
          Classes that already have a class teacher are marked below; assigning will replace
          them.
        </p>

        <SearchComponent
          value={search}
          onChange={setSearch}
          debounceMs={200}
          placeholder="Search classes..."
          className="max-w-none"
        />

        <ul className="max-h-80 space-y-2 overflow-y-auto">
          {classes.length === 0 ? (
            <li className="rounded-lg border border-slate-200 bg-slate-50 px-3 py-4 text-sm text-slate-500">
              {emptyMessage}
            </li>
          ) : (
            classes.map((classItem) => {
              const isSelected = selected?.id === classItem.id
              const statusLabel = classItem.is_assigned
                ? `Assigned: ${classItem.class_teacher?.full_name ?? 'Teacher'}`
                : 'No class teacher'

              return (
                <li key={classItem.id}>
                  <button
                    type="button"
                    onClick={() => setSelected(classItem)}
                    className={mergeClasses(
                      'flex w-full items-start justify-between gap-3 rounded-lg border px-3 py-3 text-left transition-colors',
                      isSelected
                        ? 'border-blue-400 bg-blue-50'
                        : 'border-slate-200 bg-white hover:border-slate-300 hover:bg-slate-50',
                    )}
                  >
                    <div className="min-w-0 space-y-1">
                      <p className="font-medium text-slate-900">{classItem.name}</p>
                      <p className="text-sm text-slate-500">{classItem.level_name}</p>
                    </div>
                    <span
                      className={mergeClasses(
                        'shrink-0 text-xs font-medium',
                        classItem.is_assigned ? 'text-amber-700' : 'text-emerald-700',
                      )}
                    >
                      {statusLabel}
                    </span>
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
            onClick={() => assign()}
            disabled={!selected || isPending}
            loading={isPending}
          >
            Assign Class
          </Button>
        </div>
      </div>
    </Modal>
  )
}

export default AssignClassToTeacherModal
