import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate, useSearchParams } from 'react-router-dom'
import CorrectionsInbox from '@/features/assessments/components/CorrectionsInbox'
import TeacherAssignmentsWorkspace, {
  TAB_MANAGED,
  TAB_SUBJECT,
  type TeacherAssignmentTab,
} from '@/features/staff/components/TeacherAssignmentsWorkspace'
import { getMyTeaching } from '@/features/staff/services'
import { getApiErrorMessage } from '@/utils'

const MY_TEACHING_QUERY_KEY = ['me', 'teaching'] as const

const tabFromParam = (value: string | null): TeacherAssignmentTab | null => {
  if (value === 'managed') return TAB_MANAGED
  if (value === 'subject') return TAB_SUBJECT
  return null
}

const paramFromTab = (tab: TeacherAssignmentTab) =>
  tab === TAB_SUBJECT ? 'subject' : 'managed'

const TeacherClassesWorkspace = () => {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [inboxOpen, setInboxOpen] = useState(false)
  const { data, isLoading, isError, error } = useQuery({
    queryKey: MY_TEACHING_QUERY_KEY,
    queryFn: getMyTeaching,
  })

  const managed = data?.class_teacher_assignments ?? []
  const teaching = data?.teaching_assignments ?? []
  const teachingIds = useMemo(() => new Set(teaching.map((item) => item.id)), [teaching])
  const inbox = data?.corrections_inbox ?? []
  const inboxCount = data?.corrections_inbox_count ?? inbox.length

  const defaultTab = useMemo(
    () => (managed.length === 0 && teaching.length > 0 ? TAB_SUBJECT : TAB_MANAGED),
    [managed.length, teaching.length],
  )

  const activeTab = tabFromParam(searchParams.get('tab')) ?? defaultTab

  const handleTabChange = (tab: TeacherAssignmentTab) => {
    const next = new URLSearchParams(searchParams)
    next.set('tab', paramFromTab(tab))
    setSearchParams(next, { replace: true })
  }

  if (isLoading) {
    return <p className="text-sm text-slate-500 py-8">Loading your classes…</p>
  }

  if (isError || !data) {
    return (
      <p className="text-sm text-red-600 py-8" role="alert">
        {getApiErrorMessage(error, 'Unable to load your teaching assignments.')}
      </p>
    )
  }

  return (
    <>
      <TeacherAssignmentsWorkspace
        managed={managed}
        teaching={teaching}
        activeTab={activeTab}
        onTabChange={handleTabChange}
        classActionLabel="View class"
        subjectActionLabel="View subject"
        requireViewStream
        subjectTabExtra={
          <button
            type="button"
            onClick={() => setInboxOpen(true)}
            className="rounded-full bg-orange-50 px-3 py-1 text-xs font-medium text-orange-800 hover:bg-orange-100 cursor-pointer"
          >
            Corrections {inboxCount}
          </button>
        }
        onClassAction={(assignment) => {
          if (!assignment.view_stream_id) return
          navigate(`/classes/${assignment.view_stream_id}`)
        }}
        onSubjectAction={(assignment) => {
          navigate(`/classes/subjects/${assignment.id}`)
        }}
      />

      <CorrectionsInbox
        open={inboxOpen}
        onClose={() => setInboxOpen(false)}
        items={inbox}
        title="Corrections"
        emptyLabel="No subjects need correction right now."
        onOpenItem={(item) => {
          const match = item.subjects.find((subject) =>
            teachingIds.has(subject.teaching_assignment_id),
          )
          if (match) {
            navigate(`/classes/subjects/${match.teaching_assignment_id}`)
          }
        }}
      />
    </>
  )
}

export default TeacherClassesWorkspace
