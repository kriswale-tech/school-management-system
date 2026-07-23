import type {
  ClassForSetup,
  ClassSubjectForSetup,
  LevelForSetup,
  LevelWithRelatedClassesAndSubjects,
  StreamForSetup,
} from '@/features/setup/classes-and-subjects/types'
import type {
  ClassTeacherAssignment,
  Teacher,
  TeacherFormData,
  TeacherGender,
  TeachingAssignment,
} from './types'

export const DEFAULT_PROFILE_IMAGE = '/images/default_profile.webp'
export const WHOLE_CLASS_VALUE = '__whole_class__'
export const NO_SUBJECT_GROUP_VALUE = '__no_subject_group__'

export type ClassOption = {
  id: string
  name: string
  levelName: string
  streams: StreamForSetup[]
  subjects: ClassSubjectForSetup[]
}

export const getTeacherProfileImage = (teacher: Teacher) =>
  teacher.profile.profile_picture ?? DEFAULT_PROFILE_IMAGE

export const mapTeacherToFormData = (teacher: Teacher): TeacherFormData => {
  const gender = teacher.profile.gender

  return {
    first_name: teacher.first_name,
    last_name: teacher.last_name,
    gender: gender === 'male' || gender === 'female' ? (gender as TeacherGender) : undefined,
    phone_number: teacher.phone_number,
    phone_number_alt: teacher.profile.phone_number_alt ?? '',
    email: teacher.email ?? '',
    date_of_birth: teacher.profile.date_of_birth ?? '',
    address: teacher.profile.address ?? '',
  }
}

export const buildClassOptions = (
  levels: LevelWithRelatedClassesAndSubjects,
): ClassOption[] => {
  return levels.flatMap((level) =>
    level.classes
      .filter((cls): cls is ClassForSetup & { id: string } => Boolean(cls.id))
      .map((cls) => ({
        id: cls.id,
        name: cls.name,
        levelName: level.name,
        streams: cls.streams ?? [],
        subjects: getSubjectsForClass(level, cls),
      })),
  )
}

function getSubjectsForClass(level: LevelForSetup, cls: ClassForSetup & { id: string }) {
  if (level.subject_scope === 'class') {
    return (cls.subjects ?? []).filter((subject) => subject.class_subject_id)
  }

  return level.subjects
    .filter((subject) => subject.id && subject.class_ids.includes(cls.id))
    .map((subject) => {
      const classSubject = cls.subjects?.find((item) => item.id === subject.id)
      if (!classSubject?.class_subject_id) return null
      return classSubject
    })
    .filter((subject): subject is ClassSubjectForSetup => Boolean(subject))
}

export const formatClassTeacherAssignmentLabel = (assignment: ClassTeacherAssignment) =>
  formatClassDisplayName(assignment.class_level_name, assignment.stream_name)

export const formatTeachingAssignmentLabel = (assignment: TeachingAssignment) => {
  const parts = [
    assignment.class_level_name,
    assignment.subject_name,
    assignment.stream_name,
    assignment.subject_group_name,
  ].filter(Boolean)

  return parts.join(' · ')
}

export const isClassTeacherSlotAssigned = (
  assignments: ClassTeacherAssignment[],
  classLevelId: string,
  streamId: string | null,
) =>
  assignments.some(
    (assignment) =>
      assignment.class_level_id === classLevelId &&
      (assignment.stream_id ?? null) === streamId,
  )

export const isTeachingSlotAssigned = (
  assignments: TeachingAssignment[],
  classSubjectId: string,
  streamId: string | null,
  subjectGroupId: string | null,
) =>
  assignments.some(
    (assignment) =>
      assignment.class_subject_id === classSubjectId &&
      (assignment.stream_id ?? null) === streamId &&
      (assignment.subject_group_id ?? null) === subjectGroupId,
  )

export const formatClassDisplayName = (
  classLevelName: string,
  streamName?: string | null,
): string => {
  const trimmedStream = streamName?.trim()
  if (trimmedStream) {
    return `${classLevelName} ${trimmedStream}`
  }
  return classLevelName
}

export const formatClassTeacherAssignmentsLabel = (
  assignments: ClassTeacherAssignment[],
): string => {
  if (assignments.length === 0) return '-'

  const classNames = assignments.map((assignment) =>
    formatClassDisplayName(assignment.class_level_name, assignment.stream_name),
  )

  if (classNames.length === 1) return classNames[0]
  if (classNames.length === 2) return classNames.join('/')
  return `${classNames[0]}/${classNames[1]}/...`
}

export const formatTeachingAssignmentsLabel = (count: number): string => {
  if (count === 0) return 'No subjects assigned'
  if (count === 1) return '1 Subject assigned'
  return `${count} Subjects assigned`
}
