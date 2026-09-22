import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { isAxiosError } from 'axios'
import { useEffect, useRef, useState } from 'react'
import toast from 'react-hot-toast'
import { useParams, useSearchParams } from 'react-router-dom'
import ActionBar from '@/components/shared/ActionBar'
import { Button } from '@/components/ui'
import {
  generateStudentReport,
  getStoredStudentReport,
} from '@/features/classes/services'
import { getApiErrorMessage } from '@/utils'

const StudentReportPreview = () => {
  const { streamId, studentId } = useParams<{ streamId: string; studentId: string }>()
  const [searchParams] = useSearchParams()
  const termId = searchParams.get('term') ?? undefined
  const queryClient = useQueryClient()
  const autoGenerateStarted = useRef(false)
  const [shareBusy, setShareBusy] = useState(false)

  const reportQuery = useQuery({
    queryKey: ['assessments', 'report-pdf', streamId, studentId, termId],
    queryFn: () => getStoredStudentReport(streamId!, studentId!, termId),
    enabled: Boolean(streamId && studentId),
    retry: false,
  })

  const generateMutation = useMutation({
    mutationFn: () => generateStudentReport(streamId!, studentId!, termId),
    onSuccess: (data) => {
      queryClient.setQueryData(
        ['assessments', 'report-pdf', streamId, studentId, termId],
        data,
      )
    },
  })

  const missingReport =
    reportQuery.isError &&
    isAxiosError(reportQuery.error) &&
    reportQuery.error.response?.status === 404

  useEffect(() => {
    autoGenerateStarted.current = false
  }, [streamId, studentId, termId])

  useEffect(() => {
    if (!streamId || !studentId) return
    if (!missingReport) return
    if (autoGenerateStarted.current) return
    if (generateMutation.isPending) return
    autoGenerateStarted.current = true
    generateMutation.mutate()
  }, [
    streamId,
    studentId,
    missingReport,
    generateMutation.isPending,
    generateMutation.mutate,
  ])

  const report = reportQuery.data ?? generateMutation.data
  const hasReadyReport = Boolean(report?.url && report.status === 'ready')
  const isGenerating =
    generateMutation.isPending ||
    (missingReport && !generateMutation.isError && !hasReadyReport)

  const generateFailed = generateMutation.isError
  const loadFailed =
    reportQuery.isError && !missingReport && !hasReadyReport

  const errorMessage = generateFailed
    ? getApiErrorMessage(generateMutation.error, 'Unable to generate report.')
    : loadFailed
      ? getApiErrorMessage(reportQuery.error, 'Unable to load report.')
      : null

  // Regenerate only when generation failed, or another non-404 load error.
  const showRegenerate = generateFailed || loadFailed

  const handleRegenerate = () => {
    generateMutation.mutate()
  }

  const handleShare = async () => {
    if (!report?.url) return
    setShareBusy(true)
    try {
      if (typeof navigator.share === 'function') {
        await navigator.share({
          title: 'Student report',
          url: report.url,
        })
        return
      }
      await navigator.clipboard.writeText(report.url)
      toast.success('Report link copied')
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') return
      try {
        await navigator.clipboard.writeText(report.url)
        toast.success('Report link copied')
      } catch {
        toast.error('Unable to share report link')
      }
    } finally {
      setShareBusy(false)
    }
  }

  return (
    <div className="flex min-h-screen flex-col bg-slate-100">
      <ActionBar back title="Report">
        <div className="flex items-center gap-2">
          {hasReadyReport ? (
            <>
              <Button
                type="button"
                variant="outline"
                className="max-w-fit py-2 text-sm"
                onClick={() => window.open(report!.url!, '_blank', 'noopener,noreferrer')}
              >
                Open in new tab
              </Button>
              <Button
                type="button"
                variant="outline"
                className="max-w-fit py-2 text-sm"
                onClick={handleShare}
                disabled={shareBusy}
              >
                Share
              </Button>
            </>
          ) : null}
          {showRegenerate ? (
            <Button
              type="button"
              className="max-w-fit py-2 text-sm"
              onClick={handleRegenerate}
              disabled={!streamId || !studentId || generateMutation.isPending}
            >
              {generateMutation.isPending ? 'Generating…' : 'Regenerate'}
            </Button>
          ) : null}
        </div>
      </ActionBar>

      <div className="flex flex-1 flex-col px-4 py-6">
        {reportQuery.isLoading || isGenerating ? (
          <p className="text-sm text-slate-500">
            {isGenerating ? 'Generating PDF report…' : 'Loading report…'}
          </p>
        ) : errorMessage ? (
          <div className="space-y-2" role="alert">
            <p className="text-sm text-red-600">{errorMessage}</p>
            <p className="text-sm text-slate-500">
              The report file could not be loaded. Use Regenerate to create it again.
            </p>
          </div>
        ) : hasReadyReport ? (
          <iframe
            title="Student report PDF"
            src={report!.url!}
            className="min-h-[80vh] w-full flex-1 rounded-md border border-slate-200 bg-white"
          />
        ) : (
          <p className="text-sm text-slate-500">No report available yet.</p>
        )}
      </div>
    </div>
  )
}

export default StudentReportPreview
