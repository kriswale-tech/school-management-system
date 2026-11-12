import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { isAxiosError } from 'axios'
import { useEffect, useRef, useState } from 'react'
import toast from 'react-hot-toast'
import ActionBar from '@/components/shared/ActionBar'
import { Button } from '@/components/ui'
import type { StoredStudentReport } from '@/features/classes/assessment/types'
import { getApiErrorMessage } from '@/utils'

type StudentReportViewerProps = {
  enabled: boolean
  queryKey: readonly unknown[]
  getReport: () => Promise<StoredStudentReport>
  generateReport: (options?: { force?: boolean }) => Promise<StoredStudentReport>
  variant?: 'page' | 'embed'
  autoLoad?: boolean
  onNotifyParents?: () => void
}

const StudentReportViewer = ({
  enabled,
  queryKey,
  getReport,
  generateReport,
  variant = 'embed',
  autoLoad,
  onNotifyParents,
}: StudentReportViewerProps) => {
  const queryClient = useQueryClient()
  const queryKeyValue = queryKey.join(':')
  const shouldAutoLoad = autoLoad ?? variant === 'page'
  const autoGenerateStarted = useRef(false)
  const [requestedKey, setRequestedKey] = useState<string | null>(null)
  const requested = requestedKey === queryKeyValue
  const loadEnabled = enabled && (shouldAutoLoad || requested)

  const reportQuery = useQuery({
    queryKey: [...queryKey],
    queryFn: getReport,
    enabled: loadEnabled,
    retry: false,
  })

  const {
    mutate: runGenerate,
    reset: resetGenerate,
    data: generatedReport,
    error: generateError,
    isPending: isGeneratePending,
    isError: isGenerateError,
  } = useMutation({
    mutationFn: (options?: { force?: boolean }) => generateReport(options),
    onSuccess: (data) => {
      queryClient.setQueryData([...queryKey], data)
      toast.success('Report ready')
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, 'Unable to generate report.'))
    },
  })

  const missingReport =
    reportQuery.isError &&
    isAxiosError(reportQuery.error) &&
    reportQuery.error.response?.status === 404

  useEffect(() => {
    autoGenerateStarted.current = false
    resetGenerate()
  }, [queryKeyValue, resetGenerate])

  useEffect(() => {
    if (!loadEnabled) return
    if (!missingReport) return
    if (autoGenerateStarted.current) return
    if (isGeneratePending) return
    autoGenerateStarted.current = true
    runGenerate(undefined)
  }, [loadEnabled, missingReport, isGeneratePending, runGenerate])

  const report = reportQuery.data ?? generatedReport
  const hasReadyReport = Boolean(report?.url && report.status === 'ready')
  const isGenerating =
    isGeneratePending || (missingReport && !isGenerateError && !hasReadyReport)

  const generateFailed = isGenerateError
  const loadFailed = reportQuery.isError && !missingReport && !hasReadyReport

  const errorMessage = generateFailed
    ? getApiErrorMessage(generateError, 'Unable to generate report.')
    : loadFailed
      ? getApiErrorMessage(reportQuery.error, 'Unable to load report.')
      : null

  const showRegenerate = hasReadyReport || generateFailed || loadFailed

  const actions = (
    <div className="flex flex-wrap items-center gap-2">
      {hasReadyReport ? (
        <>
          <Button
            type="button"
            variant="outline"
            className="max-w-fit py-2 text-sm"
            onClick={() => window.open(report!.url!, '_blank', 'noopener,noreferrer')}
            disabled={isGeneratePending}
          >
            Open in new tab
          </Button>
          {onNotifyParents ? (
            <Button
              type="button"
              variant="outline"
              className="max-w-fit py-2 text-sm"
              onClick={onNotifyParents}
              disabled={isGeneratePending}
            >
              Send to guardians
            </Button>
          ) : null}
        </>
      ) : (
        <Button
          type="button"
          className="max-w-fit py-2 text-sm"
          loading={loadEnabled && isGenerating}
          loadingText="Generating"
          disabled={!enabled || isGeneratePending}
          onClick={() => {
            setRequestedKey(queryKeyValue)
            if (missingReport || generateFailed) {
              runGenerate({ force: Boolean(generateFailed) })
            }
          }}
        >
          Generate report
        </Button>
      )}
      {showRegenerate ? (
        <Button
          type="button"
          variant="outline"
          className="max-w-fit py-2 text-sm"
          loading={isGeneratePending}
          loadingText="Generating"
          onClick={() => runGenerate({ force: true })}
          disabled={!enabled || isGeneratePending}
        >
          Regenerate
        </Button>
      ) : null}
    </div>
  )

  const showBody = shouldAutoLoad || requested || hasReadyReport

  const body = showBody ? (
    <>
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
          className={
            variant === 'page'
              ? 'min-h-[80vh] w-full flex-1 rounded-md border border-slate-200 bg-white'
              : 'min-h-[80vh] w-full rounded-md border border-slate-200 bg-white'
          }
        />
      ) : (
        <p className="text-sm text-slate-500">No report available yet.</p>
      )}
    </>
  ) : null

  if (variant === 'page') {
    return (
      <div className="flex min-h-screen flex-col bg-slate-100">
        <ActionBar back title="Report">
          {actions}
        </ActionBar>
        <div className="flex flex-1 flex-col px-4 py-6">{body}</div>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center justify-end">{actions}</div>
      {body}
    </div>
  )
}

export default StudentReportViewer
