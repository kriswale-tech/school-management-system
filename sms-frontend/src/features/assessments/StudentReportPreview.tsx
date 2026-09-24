import { useParams, useSearchParams } from 'react-router-dom'
import StudentReportViewer from './components/StudentReportViewer'
import { generateStudentReport, getStoredStudentReport } from '@/features/classes/services'

const StudentReportPreview = () => {
  const { streamId, studentId } = useParams<{ streamId: string; studentId: string }>()
  const [searchParams] = useSearchParams()
  const termId = searchParams.get('term') ?? undefined

  return (
    <StudentReportViewer
      variant="page"
      enabled={Boolean(streamId && studentId)}
      queryKey={['assessments', 'report-pdf', streamId, studentId, termId]}
      getReport={() => getStoredStudentReport(streamId!, studentId!, termId)}
      generateReport={() => generateStudentReport(streamId!, studentId!, termId)}
    />
  )
}

export default StudentReportPreview
