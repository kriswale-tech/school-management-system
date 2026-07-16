import { useState } from 'react'
import AssignSubjectModal from '../AssignSubjectModal'
import type { ClassForSetup, SubjectForSetup } from '../../types'
import type { ClassSubjectSetupHandlers } from '../../class-subject-setup-handlers'
import type { AddStreamPayload } from '../../class-subject-setup-types'
import type { ConfirmState } from './types'
import StreamsDropdown from './StreamsDropdown'
import SubjectCountDropdown from './SubjectCountDropdown'

const StreamAndSubjectMiniButtons = ({
  data,
  levelSubjects,
  handlers,
  onConfirm,
  onEditStream,
}: {
  data: ClassForSetup
  levelSubjects: SubjectForSetup[]
  handlers: ClassSubjectSetupHandlers
  onConfirm: (state: ConfirmState) => void
  onEditStream: (streamId: string, initialValues: AddStreamPayload) => void
}) => {
  const showStreamButton = data.streams && data.streams.length > 0
  const classId = data.id
  const [assignOpen, setAssignOpen] = useState(false)

  return (
    <div className="flex items-center gap-2">
      {showStreamButton && (
        <StreamsDropdown
          streams={data.streams ?? []}
          onEdit={onEditStream}
          onDelete={(streamId, name) => onConfirm({ type: 'deleteStream', streamId, name })}
        />
      )}
      {classId && (
        <SubjectCountDropdown
          subjects={data.subjects ?? []}
          onRemove={(subjectId, subjectName) =>
            onConfirm({
              type: 'removeSubjectFromClass',
              classId,
              subjectId,
              subjectName,
              className: data.name,
            })
          }
          onAddSubject={() => setAssignOpen(true)}
        />
      )}

      {classId && (
        <AssignSubjectModal
          open={assignOpen}
          targetClassName={data.name}
          subjects={levelSubjects}
          assignedSubjectIds={(data.subjects ?? []).map((subject) => subject.id)}
          onClose={() => setAssignOpen(false)}
          onSubmit={(subjectId) => {
            handlers.onAssignSubjectToClass(classId, subjectId)
            setAssignOpen(false)
          }}
        />
      )}
    </div>
  )
}

export default StreamAndSubjectMiniButtons
