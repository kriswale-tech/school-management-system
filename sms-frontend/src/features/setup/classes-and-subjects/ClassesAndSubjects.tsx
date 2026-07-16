import toast from 'react-hot-toast'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import ClassSubjectForm from './components/ClassSubjectForm'
import {
  activateOrDeactivateClass,
  activateOrDeactivateLevel,
  activateOrDeactivateSubject,
  addClass,
  addStream,
  addSubject,
  addSubjectGroup,
  deleteClass,
  deleteStream,
  deleteSubject,
  deleteSubjectGroup,
  editClass,
  editStream,
  editSubject,
  editSubjectGroup,
  assignSubjectToClass,
  removeSubjectFromClass,
} from './class-subject-setup-services'
import { getClassAndSubjects, updateClassAndSubjectsSetup } from './services'
import { handleSetupProgressResponse } from '@/features/setup/utils/handle-setup-progress-response'
import { useAuthStore } from '@/features/auth/store'
import LoadingSpinner from '@/components/ui/LoadingSpinner'
import { getApiErrorMessage } from '@/utils'
import type { ClassSubjectSetupHandlers } from './class-subject-setup-handlers'

const ClassesAndSubjects = () => {
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const setUser = useAuthStore((state) => state.setUser)
  const user = useAuthStore((state) => state.user)

  const { data, isLoading } = useQuery({
    queryKey: ['classAndSubjects'],
    queryFn: getClassAndSubjects,
  })

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ['classAndSubjects'] })
  }

  const onMutationError = (fallback: string) => (error: unknown) => {
    toast.error(getApiErrorMessage(error, fallback))
  }

  const onMutationSuccess = (message: string) => () => {
    toast.success(message)
    invalidate()
  }

  const { mutate: completeSetup, isPending: isCompleting } = useMutation({
    mutationFn: updateClassAndSubjectsSetup,
    onSuccess: (response) => {
      toast.success('Classes and subjects saved')
      void queryClient.invalidateQueries({ queryKey: ['setup'] })
      handleSetupProgressResponse(response, { navigate, user, setUser })
    },
    onError: onMutationError('Unable to complete classes and subjects setup'),
  })

  const { mutate: toggleLevel } = useMutation({
    mutationFn: ({ levelId, isActive }: { levelId: string; isActive: boolean }) =>
      activateOrDeactivateLevel(levelId, isActive),
    onSuccess: onMutationSuccess('Level updated'),
    onError: onMutationError('Unable to update level'),
  })

  const { mutate: createClass } = useMutation({
    mutationFn: ({ levelId, payload }: { levelId: string; payload: Parameters<typeof addClass>[1] }) =>
      addClass(levelId, payload),
    onSuccess: onMutationSuccess('Class added'),
    onError: onMutationError('Unable to add class'),
  })

  const { mutate: updateClass } = useMutation({
    mutationFn: ({
      classId,
      payload,
    }: {
      classId: string
      payload: Parameters<typeof editClass>[1]
    }) => editClass(classId, payload),
    onSuccess: onMutationSuccess('Class updated'),
    onError: onMutationError('Unable to update class'),
  })

  const { mutate: removeClass } = useMutation({
    mutationFn: deleteClass,
    onSuccess: onMutationSuccess('Class deleted'),
    onError: onMutationError('Unable to delete class'),
  })

  const { mutate: toggleClass } = useMutation({
    mutationFn: ({ classId, isActive }: { classId: string; isActive: boolean }) =>
      activateOrDeactivateClass(classId, isActive),
    onSuccess: onMutationSuccess('Class updated'),
    onError: onMutationError('Unable to update class'),
  })

  const { mutate: createSubject } = useMutation({
    mutationFn: addSubject,
    onSuccess: onMutationSuccess('Subject added'),
    onError: onMutationError('Unable to add subject'),
  })

  const { mutate: updateSubject } = useMutation({
    mutationFn: ({
      subjectId,
      payload,
    }: {
      subjectId: string
      payload: Parameters<typeof editSubject>[1]
    }) => editSubject(subjectId, payload),
    onSuccess: onMutationSuccess('Subject updated'),
    onError: onMutationError('Unable to update subject'),
  })

  const { mutate: removeSubject } = useMutation({
    mutationFn: deleteSubject,
    onSuccess: onMutationSuccess('Subject deleted'),
    onError: onMutationError('Unable to delete subject'),
  })

  const { mutate: toggleSubject } = useMutation({
    mutationFn: ({ subjectId, isActive }: { subjectId: string; isActive: boolean }) =>
      activateOrDeactivateSubject(subjectId, isActive),
    onSuccess: onMutationSuccess('Subject updated'),
    onError: onMutationError('Unable to update subject'),
  })

  const { mutate: createStream } = useMutation({
    mutationFn: ({
      classId,
      payload,
    }: {
      classId: string
      payload: Parameters<typeof addStream>[1]
    }) => addStream(classId, payload),
    onSuccess: onMutationSuccess('Stream added'),
    onError: onMutationError('Unable to add stream'),
  })

  const { mutate: updateStream } = useMutation({
    mutationFn: ({
      streamId,
      payload,
    }: {
      streamId: string
      payload: Parameters<typeof editStream>[1]
    }) => editStream(streamId, payload),
    onSuccess: onMutationSuccess('Stream updated'),
    onError: onMutationError('Unable to update stream'),
  })

  const { mutate: removeStream } = useMutation({
    mutationFn: deleteStream,
    onSuccess: onMutationSuccess('Stream removed'),
    onError: onMutationError('Unable to remove stream'),
  })

  const { mutate: createSubjectGroup } = useMutation({
    mutationFn: ({
      levelId,
      subjectId,
      payload,
    }: {
      levelId: string
      subjectId: string
      payload: { name: string }
    }) => addSubjectGroup(levelId, subjectId, payload),
    onSuccess: onMutationSuccess('Group added'),
    onError: onMutationError('Unable to add group'),
  })

  const { mutate: updateSubjectGroup } = useMutation({
    mutationFn: ({
      groupId,
      payload,
    }: {
      groupId: string
      payload: { name: string }
    }) => editSubjectGroup(groupId, payload),
    onSuccess: onMutationSuccess('Group updated'),
    onError: onMutationError('Unable to update group'),
  })

  const { mutate: removeSubjectGroup } = useMutation({
    mutationFn: deleteSubjectGroup,
    onSuccess: onMutationSuccess('Group removed'),
    onError: onMutationError('Unable to remove group'),
  })

  const { mutate: attachSubjectToClass } = useMutation({
    mutationFn: ({ classId, subjectId }: { classId: string; subjectId: string }) =>
      assignSubjectToClass(classId, subjectId),
    onSuccess: onMutationSuccess('Subject assigned to class'),
    onError: onMutationError('Unable to assign subject to class'),
  })

  const { mutate: detachSubjectFromClass } = useMutation({
    mutationFn: ({ classId, subjectId }: { classId: string; subjectId: string }) =>
      removeSubjectFromClass(classId, subjectId),
    onSuccess: onMutationSuccess('Subject removed from class'),
    onError: onMutationError('Unable to remove subject from class'),
  })

  const handlers: ClassSubjectSetupHandlers = {
    onComplete: () => completeSetup(),
    isCompleting,
    onLevelActiveChange: (levelId, isActive) => toggleLevel({ levelId, isActive }),
    onAddClass: (levelId, payload) => createClass({ levelId, payload }),
    onEditClass: (classId, payload) => updateClass({ classId, payload }),
    onDeleteClass: (classId) => removeClass(classId),
    onClassActiveChange: (classId, isActive) => toggleClass({ classId, isActive }),
    onAddSubject: (payload) => createSubject(payload),
    onEditSubject: (subjectId, payload) => updateSubject({ subjectId, payload }),
    onDeleteSubject: (subjectId) => removeSubject(subjectId),
    onSubjectActiveChange: (subjectId, isActive) => toggleSubject({ subjectId, isActive }),
    onAddStream: (classId, payload) => createStream({ classId, payload }),
    onEditStream: (streamId, payload) => updateStream({ streamId, payload }),
    onDeleteStream: (streamId) => removeStream(streamId),
    onAddSubjectGroup: (levelId, subjectId, payload) =>
      createSubjectGroup({ levelId, subjectId, payload }),
    onEditSubjectGroup: (groupId, payload) => updateSubjectGroup({ groupId, payload }),
    onDeleteSubjectGroup: (groupId) => removeSubjectGroup(groupId),
    onAssignSubjectToClass: (classId, subjectId) => attachSubjectToClass({ classId, subjectId }),
    onRemoveSubjectFromClass: (classId, subjectId) =>
      detachSubjectFromClass({ classId, subjectId }),
  }

  if (isLoading) return <LoadingSpinner className="mx-auto" />

  return <ClassSubjectForm levels={data ?? []} handlers={handlers} />
}

export default ClassesAndSubjects
