export type ConfirmState =
  | { type: 'deleteClass'; classId: string; name: string }
  | { type: 'deleteSubject'; subjectId: string; name: string }
  | { type: 'deleteStream'; streamId: string; name: string }
  | { type: 'deleteGroup'; groupId: string; name: string }
  | {
      type: 'removeSubjectFromClass'
      classId: string
      subjectId: string
      subjectName: string
      className: string
    }
  | null
