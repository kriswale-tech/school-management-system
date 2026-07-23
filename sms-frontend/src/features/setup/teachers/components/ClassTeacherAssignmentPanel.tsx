import toast from 'react-hot-toast'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { ChoicePillGroup } from '@/components/shared'
import { Button, FormLabel, SelectField } from '@/components/ui'
import { getApiErrorMessage } from '@/utils'
import { createClassTeacherAssignment } from '../services'
import type { ClassTeacherAssignment, Teacher } from '../types'
import type { ClassOption } from '../utils'
import {
  formatClassTeacherAssignmentLabel,
  isClassTeacherSlotAssigned,
  WHOLE_CLASS_VALUE,
} from '../utils'
import AssignmentList from './AssignmentList'

type ClassTeacherAssignmentPanelProps = {
  teacher: Teacher
  classOptions: ClassOption[]
  onRequestRemove: (assignment: ClassTeacherAssignment) => void
}

const ClassTeacherAssignmentPanel = ({
  teacher,
  classOptions,
  onRequestRemove,
}: ClassTeacherAssignmentPanelProps) => {
  const queryClient = useQueryClient()
  const [classLevelId, setClassLevelId] = useState('')
  const [streamSelection, setStreamSelection] = useState(WHOLE_CLASS_VALUE)

  const selectedClass = useMemo(
    () => classOptions.find((option) => option.id === classLevelId) ?? null,
    [classLevelId, classOptions],
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

  const { mutate: assignClassTeacher, isPending } = useMutation({
    mutationFn: createClassTeacherAssignment,
    onSuccess: () => {
      toast.success('Class teacher assignment added')
      void queryClient.invalidateQueries({ queryKey: ['teachers'] })
      setClassLevelId('')
      setStreamSelection(WHOLE_CLASS_VALUE)
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, 'Unable to assign class teacher'))
    },
  })

  const handleAssign = () => {
    if (!classLevelId) {
      toast.error('Select a class')
      return
    }

    const streamId = streamSelection === WHOLE_CLASS_VALUE ? null : streamSelection

    if (isClassTeacherSlotAssigned(teacher.class_teacher_assignments, classLevelId, streamId)) {
      toast.error('This class teacher slot is already assigned')
      return
    }

    assignClassTeacher({
      teacher_id: teacher.id,
      class_level_id: classLevelId,
      stream_id: streamId,
    })
  }

  const handleClassChange = (value: string) => {
    setClassLevelId(value)
    setStreamSelection(WHOLE_CLASS_VALUE)
  }

  return (
    <div className="space-y-6">
      <AssignmentList
        title="Current class teacher roles"
        emptyMessage="No class teacher roles assigned yet."
        items={teacher.class_teacher_assignments.map((assignment) => ({
          id: assignment.id,
          label: formatClassTeacherAssignmentLabel(assignment),
        }))}
        onRemove={(assignmentId) => {
          const assignment = teacher.class_teacher_assignments.find((item) => item.id === assignmentId)
          if (assignment) onRequestRemove(assignment)
        }}
      />

      <div className="space-y-4 rounded-lg border border-slate-200 bg-slate-50 p-4">
        <p className="text-sm font-medium text-slate-900">Assign as class teacher</p>

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

        {streamItems.length > 0 ? (
          <div className="space-y-2">
            <FormLabel label="Stream" className="font-normal text-base" />
            <ChoicePillGroup
              name="class-teacher-stream"
              items={streamItems}
              value={streamSelection}
              onChange={setStreamSelection}
            />
          </div>
        ) : null}

        <Button type="button" onClick={handleAssign} loading={isPending} disabled={!classLevelId}>
          Assign Class
        </Button>
      </div>
    </div>
  )
}

export default ClassTeacherAssignmentPanel
