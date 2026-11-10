import { useState } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import StudentReportViewer from './components/StudentReportViewer'
import ReportReadyModal from './components/ReportReadyModal'
import { generateStudentReport, getStoredStudentReport } from '@/features/classes/services'

const StudentReportPreview = () => {
  const { streamId, studentId } = useParams<{ streamId: string; studentId: string }>()
  const [searchParams] = useSearchParams()
  const termId = searchParams.get('term') ?? undefined
  const [notifyOpen, setNotifyOpen] = useState(false)

  return (
    <>
      <StudentReportViewer
        variant="page"
        enabled={Boolean(streamId && studentId)}
        queryKey={['assessments', 'report-pdf', streamId, studentId, termId]}
        getReport={() => getStoredStudentReport(streamId!, studentId!, termId)}
        generateReport={(options) =>
          generateStudentReport(streamId!, studentId!, termId, options)
        }
        onNotifyParents={
          streamId && studentId ? () => setNotifyOpen(true) : undefined
        }
      />

      {streamId && studentId ? (
        <ReportReadyModal
          open={notifyOpen}
          streamId={streamId}
          termId={termId}
          studentIds={[studentId]}
          onClose={() => setNotifyOpen(false)}
          onSent={() => setNotifyOpen(false)}
        />
      ) : null}
    </>
  )
}

export default StudentReportPreview
