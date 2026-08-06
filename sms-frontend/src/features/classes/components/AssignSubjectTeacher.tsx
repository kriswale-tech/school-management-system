import toast from 'react-hot-toast'
import { useMutation, useQuery } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { AvatarComponent, Button, Modal, SearchComponent } from '@/components/ui'
import { getApiErrorMessage, mergeClasses } from '@/utils'
import { assignSubjectTeacher, getClassTeacherOptions } from '../services'
import type { ClassSubjectRow } from '../types'

type AssignSubjectTeacherProps = {
  open: boolean
  streamId: string
  subject: ClassSubjectRow | null
  onClose: () => void
  onAssigned?: () => void
}

const AssignSubjectTeacher = ({
  open,
  streamId,
  subject,
  onClose,
  onAssigned,
}: AssignSubjectTeacherProps) => {
  if (!open || !subject) return null

  return (
    <AssignSubjectTeacherContent
      streamId={streamId}
      subject={subject}
      onClose={onClose}
      onAssigned={onAssigned}
    />
  )
}

type AssignSubjectTeacherContentProps = {
  streamId: string
  subject: ClassSubjectRow
  onClose: () => void
  onAssigned?: () => void
}

const AssignSubjectTeacherContent = ({
  streamId,
  subject,
  onClose,
  onAssigned,
}: AssignSubjectTeacherContentProps) => {
  const [search, setSearch] = useState('')
  const [selectedId, setSelectedId] = useState<string | null>(subject.teacher?.id ?? null)

  const { data, isLoading } = useQuery({
    queryKey: ['classes', 'teachers', { search }],
    queryFn: () => getClassTeacherOptions({ search: search || undefined }),
  })

  const teachers = data?.results ?? []

  const { mutate: saveAssignment, isPending } = useMutation({
    mutationFn: () =>
      assignSubjectTeacher(streamId, {
        teacher_id: selectedId!,
        class_subject_id: subject.class_subject_id,
        subject_group_id: subject.subject_group_id,
      }),
    onSuccess: () => {
      toast.success('Subject teacher assigned')
      onAssigned?.()
      onClose()
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, 'Unable to assign subject teacher'))
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
      title="Change Subject Teacher"
      onClose={onClose}
      scrollable
      className="max-w-lg"
    >
      <div className="space-y-4">
        <div>
          <p className="text-xs font-medium uppercase tracking-wide text-slate-400">Subject</p>
          <p className="mt-1 text-base font-medium text-slate-900">{subject.name}</p>
        </div>

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
                      <p className="text-sm text-slate-500">{teacher.teaching_summary}</p>
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

export default AssignSubjectTeacher
