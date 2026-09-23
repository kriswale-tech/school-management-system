import { Icon } from '@iconify/react'
import { useMemo, useState, type ReactNode } from 'react'
import { ButtonTabComponent } from '@/components/shared'
import { Button } from '@/components/ui'
import { mergeClasses } from '@/utils'
import type {
  StaffDeskClassTeacherAssignment,
  StaffDeskTeachingAssignment,
} from '../types'

export const TAB_MANAGED = 'Managed Classes'
export const TAB_SUBJECT = 'Subject Teaching'

export type TeacherAssignmentTab = typeof TAB_MANAGED | typeof TAB_SUBJECT

const sumStudents = (counts: number[]) => counts.reduce((total, count) => total + count, 0)

export const ManagedClassCard = ({
  assignment,
  actionLabel,
  onAction,
  actionDisabled = false,
}: {
  assignment: StaffDeskClassTeacherAssignment
  actionLabel: string
  onAction: () => void
  actionDisabled?: boolean
}) => (
  <div className="flex flex-col justify-between rounded-lg border border-slate-200 bg-white p-4 custom-shadow-sm">
    <div className="flex items-start justify-between gap-3 mb-4">
      <p className="text-base font-medium text-slate-900">{assignment.display_name}</p>
      <div className="flex items-center gap-1 text-slate-600 shrink-0">
        <Icon icon="hugeicons:user-group" className="size-4" aria-hidden />
        <span className="text-sm">{assignment.students_count}</span>
      </div>
    </div>
    <Button type="button" className="py-2 text-sm" onClick={onAction} disabled={actionDisabled}>
      {actionLabel}
    </Button>
  </div>
)

export const SubjectTeachingCard = ({
  assignment,
  actionLabel,
  onAction,
  actionDisabled = false,
}: {
  assignment: StaffDeskTeachingAssignment
  actionLabel: string
  onAction: () => void
  actionDisabled?: boolean
}) => {
  const subjectLabel = assignment.subject_group_name
    ? `${assignment.subject_name} (${assignment.subject_group_name})`
    : assignment.subject_name
  const correctionCount = assignment.needs_correction_count ?? 0

  return (
    <div
      className={mergeClasses(
        'flex flex-col justify-between rounded-lg border bg-white p-4 custom-shadow-sm',
        correctionCount > 0 ? 'border-orange-200' : 'border-slate-200',
      )}
    >
      <div className="space-y-1 mb-4">
        <div className="flex items-start justify-between gap-3">
          <p className="text-base font-medium text-slate-900">{subjectLabel}</p>
          <div className="flex items-center gap-1 text-slate-600 shrink-0">
            <Icon icon="hugeicons:user-group" className="size-4" aria-hidden />
            <span className="text-sm">{assignment.students_count}</span>
          </div>
        </div>
        <p className="text-sm text-slate-500">{assignment.display_class_name}</p>
        {correctionCount > 0 ? (
          <span className="inline-flex rounded-full bg-orange-50 px-2.5 py-0.5 text-xs font-medium text-orange-800">
            Needs correction {correctionCount}
          </span>
        ) : null}
      </div>
      <Button type="button" className="py-2 text-sm" onClick={onAction} disabled={actionDisabled}>
        {actionLabel}
      </Button>
    </div>
  )
}

type TeacherAssignmentsWorkspaceProps = {
  managed: StaffDeskClassTeacherAssignment[]
  teaching: StaffDeskTeachingAssignment[]
  classActionLabel: string
  subjectActionLabel: string
  onClassAction: (_assignment: StaffDeskClassTeacherAssignment) => void
  onSubjectAction: (_assignment: StaffDeskTeachingAssignment) => void
  /** When true, disable managed-class actions that lack a resolvable stream. */
  requireViewStream?: boolean
  footer?: ReactNode
  /** Controlled tab; when omitted the panel manages its own tab state. */
  activeTab?: TeacherAssignmentTab
  onTabChange?: (_tab: TeacherAssignmentTab) => void
  defaultTab?: TeacherAssignmentTab
  /** Optional controls shown next to the subject-teaching tab (e.g. corrections pill). */
  subjectTabExtra?: ReactNode
}

const TeacherAssignmentsWorkspace = ({
  managed,
  teaching,
  classActionLabel,
  subjectActionLabel,
  onClassAction,
  onSubjectAction,
  requireViewStream = false,
  footer,
  activeTab: controlledTab,
  onTabChange,
  defaultTab,
  subjectTabExtra,
}: TeacherAssignmentsWorkspaceProps) => {
  const initialTab =
    defaultTab ??
    (managed.length === 0 && teaching.length > 0 ? TAB_SUBJECT : TAB_MANAGED)
  const [internalTab, setInternalTab] = useState<TeacherAssignmentTab>(initialTab)
  const activeTab = controlledTab ?? internalTab

  const setActiveTab = (tab: TeacherAssignmentTab) => {
    onTabChange?.(tab)
    if (controlledTab === undefined) {
      setInternalTab(tab)
    }
  }

  const stats = useMemo(() => {
    if (activeTab === TAB_MANAGED) {
      return {
        primaryLabel: `${managed.length} ${managed.length === 1 ? 'Class' : 'Classes'}`,
        primaryIcon: 'hugeicons:notebook-01',
        students: sumStudents(managed.map((item) => item.students_count)),
      }
    }

    return {
      primaryLabel: `${teaching.length} ${teaching.length === 1 ? 'Subject' : 'Subjects'}`,
      primaryIcon: 'hugeicons:book-open-01',
      students: sumStudents(teaching.map((item) => item.students_count)),
    }
  }, [activeTab, managed, teaching])

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <ButtonTabComponent
            activeTab={activeTab}
            tabs={[
              {
                label: TAB_MANAGED,
                onClick: () => setActiveTab(TAB_MANAGED),
              },
              {
                label: TAB_SUBJECT,
                onClick: () => setActiveTab(TAB_SUBJECT),
              },
            ]}
          />
          {activeTab === TAB_SUBJECT ? subjectTabExtra : null}
        </div>
        <div className="flex items-center gap-4 text-sm text-slate-600">
          <div className="flex items-center gap-1.5">
            <Icon icon={stats.primaryIcon} className="size-4" aria-hidden />
            <span>{stats.primaryLabel}</span>
          </div>
          <div className="flex items-center gap-1.5">
            <Icon icon="hugeicons:user-group" className="size-4" aria-hidden />
            <span>
              {stats.students} {stats.students === 1 ? 'Student' : 'Students'}
            </span>
          </div>
        </div>
      </div>

      {activeTab === TAB_MANAGED ? (
        managed.length === 0 ? (
          <p className="text-sm text-slate-500 py-6">No managed classes for the active term.</p>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {managed.map((assignment) => (
              <ManagedClassCard
                key={assignment.id}
                assignment={assignment}
                actionLabel={classActionLabel}
                onAction={() => onClassAction(assignment)}
                actionDisabled={requireViewStream && !assignment.view_stream_id}
              />
            ))}
          </div>
        )
      ) : teaching.length === 0 ? (
        <p className="text-sm text-slate-500 py-6">No subject teaching for the active term.</p>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {teaching.map((assignment) => (
            <SubjectTeachingCard
              key={assignment.id}
              assignment={assignment}
              actionLabel={subjectActionLabel}
              onAction={() => onSubjectAction(assignment)}
            />
          ))}
        </div>
      )}

      {footer}
    </div>
  )
}

export default TeacherAssignmentsWorkspace
