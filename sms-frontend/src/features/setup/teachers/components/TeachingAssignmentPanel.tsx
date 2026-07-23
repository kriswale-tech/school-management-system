import toast from 'react-hot-toast'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { ChoicePillGroup } from '@/components/shared'
import { Button, FormLabel, SelectField } from '@/components/ui'
import { mergeClasses, getApiErrorMessage } from '@/utils'
import { createTeachingAssignment } from '../services'
import type { Teacher, TeachingAssignment } from '../types'
import type { ClassOption } from '../utils'
import {
  formatTeachingAssignmentLabel,
  isTeachingSlotAssigned,
  NO_SUBJECT_GROUP_VALUE,
  WHOLE_CLASS_VALUE,
} from '../utils'
import AssignmentList from './AssignmentList'

type TeachingAssignmentPanelProps = {
  teacher: Teacher
  classOptions: ClassOption[]
  onRequestRemove: (assignment: TeachingAssignment) => void
}

const TeachingAssignmentPanel = ({
  teacher,
  classOptions,
  onRequestRemove,
}: TeachingAssignmentPanelProps) => {
  const queryClient = useQueryClient()
  const [classLevelId, setClassLevelId] = useState('')
  const [classSubjectId, setClassSubjectId] = useState('')
  const [streamSelection, setStreamSelection] = useState(WHOLE_CLASS_VALUE)
  const [subjectGroupSelection, setSubjectGroupSelection] = useState(NO_SUBJECT_GROUP_VALUE)

  const selectedClass = useMemo(
    () => classOptions.find((option) => option.id === classLevelId) ?? null,
    [classLevelId, classOptions],
  )

  const selectedSubject = useMemo(
    () => selectedClass?.subjects.find((subject) => subject.class_subject_id === classSubjectId) ?? null,
    [selectedClass, classSubjectId],
  )

  const streamItems = useMemo(() => {
    if (!selectedClass || selectedClass.streams.length === 0) return []

    return [
      { label: 'Whole class', value: WHOLE_CLASS_VALUE },
      ...selectedClass.streams.map((stream) => ({
        label: stream.name,
        value: stream.id,
      })),
    ]
  }, [selectedClass])

  const subjectGroupItems = useMemo(() => {
    const groups = selectedSubject?.groups.filter((group) => group.id) ?? []
    if (groups.length === 0) return []

    return [
      { label: 'No group', value: NO_SUBJECT_GROUP_VALUE },
      ...groups.map((group) => ({
        label: group.name,
        value: group.id!,
      })),
    ]
  }, [selectedSubject])

  const { mutate: assignTeachingSubject, isPending } = useMutation({
    mutationFn: createTeachingAssignment,
    onSuccess: () => {
      toast.success('Subject assignment added')
      void queryClient.invalidateQueries({ queryKey: ['teachers'] })
      setClassLevelId('')
      setClassSubjectId('')
      setStreamSelection(WHOLE_CLASS_VALUE)
      setSubjectGroupSelection(NO_SUBJECT_GROUP_VALUE)
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, 'Unable to assign subject'))
    },
  })

  const handleClassChange = (value: string) => {
    setClassLevelId(value)
    setClassSubjectId('')
    setStreamSelection(WHOLE_CLASS_VALUE)
    setSubjectGroupSelection(NO_SUBJECT_GROUP_VALUE)
  }

  const handleSubjectChange = (subjectId: string) => {
    setClassSubjectId(subjectId)
    setStreamSelection(WHOLE_CLASS_VALUE)
    setSubjectGroupSelection(NO_SUBJECT_GROUP_VALUE)
  }

  const handleAssign = () => {
    if (!classLevelId) {
      toast.error('Select a class')
      return
    }

    if (!classSubjectId) {
      toast.error('Select a subject')
      return
    }

    const streamId = streamSelection === WHOLE_CLASS_VALUE ? null : streamSelection
    const subjectGroupId =
      subjectGroupSelection === NO_SUBJECT_GROUP_VALUE ? null : subjectGroupSelection

    if (
      isTeachingSlotAssigned(
        teacher.teaching_assignments,
        classSubjectId,
        streamId,
        subjectGroupId,
      )
    ) {
      toast.error('This subject assignment slot is already assigned')
      return
    }

    assignTeachingSubject({
      teacher_id: teacher.id,
      class_subject_id: classSubjectId,
      stream_id: streamId,
      subject_group_id: subjectGroupId,
    })
  }

  return (
    <div className="space-y-6">
      <AssignmentList
        title="Current subject assignments"
        emptyMessage="No subjects assigned yet."
        items={teacher.teaching_assignments.map((assignment) => ({
          id: assignment.id,
          label: formatTeachingAssignmentLabel(assignment),
        }))}
        onRemove={(assignmentId) => {
          const assignment = teacher.teaching_assignments.find((item) => item.id === assignmentId)
          if (assignment) onRequestRemove(assignment)
        }}
      />

      <div className="space-y-4 rounded-lg border border-slate-200 bg-slate-50 p-4">
        <p className="text-sm font-medium text-slate-900">Assign subject</p>

        <div className="space-y-2">
          <FormLabel label="Class" className="font-normal text-base" required />
          <SelectField
            options={classOptions.map((option) => ({
              value: option.id,
              label: `${option.levelName} · ${option.name}`,
            }))}
            value={classLevelId}
            onChange={handleClassChange}
            placeholder="Select class"
          />
        </div>

        <div className="space-y-2">
          <FormLabel label="Subject" className="font-normal text-base" required />
          {!selectedClass ? (
            <p className="rounded-lg border border-slate-200 bg-white px-3 py-3 text-sm text-slate-500">
              Select a class first.
            </p>
          ) : selectedClass.subjects.length === 0 ? (
            <p className="rounded-lg border border-slate-200 bg-white px-3 py-3 text-sm text-slate-500">
              No subjects are available for this class.
            </p>
          ) : (
            <div className="max-h-56 space-y-1 overflow-y-auto rounded-lg border border-slate-300 bg-white p-2">
              {selectedClass.subjects.map((subject) => {
                const isSelected = classSubjectId === subject.class_subject_id
                return (
                  <button
                    key={subject.class_subject_id}
                    type="button"
                    onClick={() => handleSubjectChange(subject.class_subject_id)}
                    className={mergeClasses(
                      'flex w-full items-center rounded-md px-3 py-2 text-left text-sm transition-colors',
                      isSelected
                        ? 'bg-slate-900 text-white'
                        : 'text-slate-700 hover:bg-slate-100',
                    )}
                  >
                    {subject.name}
                  </button>
                )
              })}
            </div>
          )}
        </div>

        {streamItems.length > 0 ? (
          <div className="space-y-2">
            <FormLabel label="Stream" className="font-normal text-base" />
            <ChoicePillGroup
              name="teaching-assignment-stream"
              items={streamItems}
              value={streamSelection}
              onChange={setStreamSelection}
            />
          </div>
        ) : null}

        {subjectGroupItems.length > 0 ? (
          <div className="space-y-2">
            <FormLabel label="Subject group" className="font-normal text-base" />
            <ChoicePillGroup
              name="teaching-assignment-group"
              items={subjectGroupItems}
              value={subjectGroupSelection}
              onChange={setSubjectGroupSelection}
            />
          </div>
        ) : null}

        <Button
          type="button"
          onClick={handleAssign}
          loading={isPending}
          disabled={!classLevelId || !classSubjectId}
        >
          Assign Subject
        </Button>
      </div>
    </div>
  )
}

export default TeachingAssignmentPanel
