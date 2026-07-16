import { useState } from 'react'
import CheckboxField from '@/components/ui/CheckboxField'
import { Icon } from '@iconify/react'
import Button from '@/components/ui/Button'
import ConfirmDialog from '@/components/shared/ConfirmDialog'
import CustomClassModal from './CustomClassModal'
import CustomSubjectModal from './CustomSubjectModal'
import StreamModal from './StreamModal'
import SubjectGroupModal from './SubjectGroupModal'
import {
  CardActionButtons,
  GroupsDropdown,
  StreamAndSubjectMiniButtons,
  StreamsDropdown,
  type ConfirmState,
} from './class-subject-card-components'
import type { ClassForSetup, SubjectForSetup, SubjectScope } from '../types'
import type { ClassSubjectSetupHandlers } from '../class-subject-setup-handlers'
import type { AddStreamPayload } from '../class-subject-setup-types'

type ClassSubjectCardProps = {
  levelId: string
  handlers: ClassSubjectSetupHandlers
  subject_scope: SubjectScope
  levelClasses?: ClassForSetup[]
  levelSubjects?: SubjectForSetup[]
} & ({ data: ClassForSetup; type: 'class' } | { data: SubjectForSetup; type: 'subject' })

type StreamModalState =
  | { mode: 'add' }
  | { mode: 'edit'; streamId: string; initialValues: AddStreamPayload }

type GroupModalState = { mode: 'add' } | { mode: 'edit'; groupId: string; initialName: string }

const ClassSubjectCard = ({
  data,
  type,
  levelId,
  handlers,
  subject_scope = 'level',
  levelClasses = [],
  levelSubjects = [],
}: ClassSubjectCardProps) => {
  const streams = type === 'class' ? (data.streams ?? []) : []
  const groups = type === 'subject' ? data.groups : []
  const showGroupsDropdown = type === 'subject' ? groups.length > 0 : streams.length > 0
  const showStreamAndSubjectMiniButtons = subject_scope === 'class' && type === 'class'
  const entityId = data.id

  const [streamModal, setStreamModal] = useState<StreamModalState | null>(null)
  const [groupModal, setGroupModal] = useState<GroupModalState | null>(null)
  const [isEditModalOpen, setIsEditModalOpen] = useState(false)
  const [confirmState, setConfirmState] = useState<ConfirmState>(null)

  const handleActiveChange = (checked: boolean) => {
    if (!entityId) return
    if (type === 'class') handlers.onClassActiveChange(entityId, checked)
    else handlers.onSubjectActiveChange(entityId, checked)
  }

  const handleConfirm = () => {
    if (!confirmState) return

    switch (confirmState.type) {
      case 'deleteClass':
        handlers.onDeleteClass(confirmState.classId)
        break
      case 'deleteSubject':
        handlers.onDeleteSubject(confirmState.subjectId)
        break
      case 'deleteStream':
        handlers.onDeleteStream(confirmState.streamId)
        break
      case 'deleteGroup':
        handlers.onDeleteSubjectGroup(confirmState.groupId)
        break
      case 'removeSubjectFromClass':
        handlers.onRemoveSubjectFromClass(confirmState.classId, confirmState.subjectId)
        break
    }

    setConfirmState(null)
  }

  const getConfirmCopy = () => {
    switch (confirmState?.type) {
      case 'deleteClass':
        return {
          title: 'Delete class',
          message: `Are you sure you want to delete "${confirmState.name}"?`,
        }
      case 'deleteSubject':
        return {
          title: 'Delete subject',
          message: `Are you sure you want to delete "${confirmState.name}"?`,
        }
      case 'deleteStream':
        return {
          title: 'Remove stream',
          message: `Are you sure you want to remove "${confirmState.name}"?`,
        }
      case 'deleteGroup':
        return {
          title: 'Remove group',
          message: `Are you sure you want to remove "${confirmState.name}"?`,
        }
      case 'removeSubjectFromClass':
        return {
          title: 'Remove subject',
          message: `Are you sure you want to remove "${confirmState.subjectName}" from "${confirmState.className}"?`,
        }
      default:
        return { title: '', message: '' }
    }
  }

  const confirmCopy = getConfirmCopy()

  return (
    <div className=" bg-white border border-slate-400 px-4 py-3 space-y-4">
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-baseline gap-2">
          <CheckboxField
            checked={data.is_active ?? false}
            onChange={(e) => handleActiveChange(e.target.checked)}
          />
          <span className="text-slate-600 text-[15px]">{data.name}</span>
        </div>

        {showStreamAndSubjectMiniButtons && type === 'class' ? (
          <StreamAndSubjectMiniButtons
            data={data}
            levelSubjects={levelSubjects}
            handlers={handlers}
            onConfirm={setConfirmState}
            onEditStream={(streamId, initialValues) =>
              setStreamModal({ mode: 'edit', streamId, initialValues })
            }
          />
        ) : (
          showGroupsDropdown &&
          (type === 'subject' ? (
            <GroupsDropdown
              groups={groups}
              onEdit={(groupId, initialName) =>
                setGroupModal({ mode: 'edit', groupId, initialName })
              }
              onDelete={(groupId, name) => setConfirmState({ type: 'deleteGroup', groupId, name })}
            />
          ) : (
            <StreamsDropdown
              streams={streams}
              onEdit={(streamId, initialValues) =>
                setStreamModal({ mode: 'edit', streamId, initialValues })
              }
              onDelete={(streamId, name) =>
                setConfirmState({ type: 'deleteStream', streamId, name })
              }
            />
          ))
        )}
      </div>

      <div className="flex items-center gap-2">
        <Button
          className="flex-1"
          variant="ghost"
          onClick={() =>
            type === 'class' ? setStreamModal({ mode: 'add' }) : setGroupModal({ mode: 'add' })
          }
        >
          <Icon
            icon="hugeicons:plus-sign"
            className="size-4 bg-white text-black rounded-full p-0.5"
          />
          <span>{type === 'class' ? 'Add Stream' : 'Add Group'}</span>
        </Button>

        {data.is_editable && entityId && (
          <CardActionButtons
            editLabel={type === 'class' ? 'Edit class' : 'Edit subject'}
            deleteLabel={type === 'class' ? 'Delete class' : 'Delete subject'}
            onEdit={() => setIsEditModalOpen(true)}
            onDelete={() =>
              setConfirmState(
                type === 'class'
                  ? { type: 'deleteClass', classId: entityId, name: data.name }
                  : { type: 'deleteSubject', subjectId: entityId, name: data.name },
              )
            }
          />
        )}
      </div>

      {type === 'class' && entityId && (
        <StreamModal
          open={streamModal !== null}
          mode={streamModal?.mode ?? 'add'}
          initialValues={streamModal?.mode === 'edit' ? streamModal.initialValues : undefined}
          onClose={() => setStreamModal(null)}
          onSubmit={(payload) => {
            if (streamModal?.mode === 'add') handlers.onAddStream(entityId, payload)
            else if (streamModal?.mode === 'edit')
              handlers.onEditStream(streamModal.streamId, payload)
            setStreamModal(null)
          }}
        />
      )}

      {type === 'subject' && entityId && (
        <SubjectGroupModal
          open={groupModal !== null}
          mode={groupModal?.mode ?? 'add'}
          initialName={groupModal?.mode === 'edit' ? groupModal.initialName : undefined}
          onClose={() => setGroupModal(null)}
          onSubmit={(payload) => {
            if (groupModal?.mode === 'add') handlers.onAddSubjectGroup(levelId, entityId, payload)
            else if (groupModal?.mode === 'edit')
              handlers.onEditSubjectGroup(groupModal.groupId, payload)
            setGroupModal(null)
          }}
        />
      )}

      {type === 'class' ? (
        <CustomClassModal
          open={isEditModalOpen}
          mode="edit"
          initialValues={{
            name: data.name,
            description: data.description ?? undefined,
            order: data.order,
          }}
          onClose={() => setIsEditModalOpen(false)}
          onSubmit={(payload) => {
            if (entityId) handlers.onEditClass(entityId, payload)
            setIsEditModalOpen(false)
          }}
        />
      ) : (
        <CustomSubjectModal
          open={isEditModalOpen}
          mode="edit"
          subjectScope={subject_scope}
          classes={levelClasses}
          initialValues={{
            name: data.name,
            classIds: data.class_ids ?? [],
          }}
          onClose={() => setIsEditModalOpen(false)}
          onSubmit={(values) => {
            if (entityId) {
              handlers.onEditSubject(entityId, {
                name: values.name,
                class_ids: values.classIds.length > 0 ? values.classIds : undefined,
              })
            }
            setIsEditModalOpen(false)
          }}
        />
      )}

      <ConfirmDialog
        open={confirmState !== null}
        title={confirmCopy.title}
        message={confirmCopy.message}
        onClose={() => setConfirmState(null)}
        onConfirm={handleConfirm}
      />
    </div>
  )
}

export default ClassSubjectCard
