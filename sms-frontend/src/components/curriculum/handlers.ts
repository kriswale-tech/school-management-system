import type { AddClassPayload, AddStreamPayload, AddSubjectPayload } from './payload-types'

export interface CurriculumHandlers {
  onLevelActiveChange: (levelId: string, isActive: boolean) => void
  onAddClass: (levelId: string, payload: AddClassPayload) => void
  onEditClass: (classId: string, payload: Partial<AddClassPayload>) => void
  onDeleteClass: (classId: string) => void
  onClassActiveChange: (classId: string, isActive: boolean) => void
  onAddSubject: (payload: AddSubjectPayload) => void
  onEditSubject: (subjectId: string, payload: Omit<AddSubjectPayload, 'level_id'>) => void
  onDeleteSubject: (subjectId: string) => void
  onSubjectActiveChange: (subjectId: string, isActive: boolean) => void
  onAddStream: (classId: string, payload: AddStreamPayload) => void
  onEditStream: (streamId: string, payload: Partial<AddStreamPayload>) => void
  onDeleteStream: (streamId: string) => void
  onAddSubjectGroup: (levelId: string, subjectId: string, payload: { name: string }) => void
  onEditSubjectGroup: (groupId: string, payload: { name: string }) => void
  onDeleteSubjectGroup: (groupId: string) => void
  onAssignSubjectToClass: (classId: string, subjectId: string) => void
  onRemoveSubjectFromClass: (classId: string, subjectId: string) => void
}
