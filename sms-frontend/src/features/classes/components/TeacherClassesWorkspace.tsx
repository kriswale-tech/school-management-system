import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import TeacherAssignmentsWorkspace from '@/features/staff/components/TeacherAssignmentsWorkspace'
import { getMyTeaching } from '@/features/staff/services'
import { getApiErrorMessage } from '@/utils'

const MY_TEACHING_QUERY_KEY = ['me', 'teaching'] as const

const TeacherClassesWorkspace = () => {
  const navigate = useNavigate()
  const { data, isLoading, isError, error } = useQuery({
    queryKey: MY_TEACHING_QUERY_KEY,
    queryFn: getMyTeaching,
  })

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

  const managed = data.class_teacher_assignments ?? []
  const teaching = data.teaching_assignments ?? []

  return (
    <TeacherAssignmentsWorkspace
      managed={managed}
      teaching={teaching}
      classActionLabel="View class"
      subjectActionLabel="View subject"
      requireViewStream
      onClassAction={(assignment) => {
        if (!assignment.view_stream_id) return
        navigate(`/classes/${assignment.view_stream_id}`)
      }}
      onSubjectAction={(assignment) => {
        navigate(`/classes/subjects/${assignment.id}`)
      }}
    />
  )
}

export default TeacherClassesWorkspace
