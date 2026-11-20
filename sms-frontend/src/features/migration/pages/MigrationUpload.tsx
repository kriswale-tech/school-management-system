import { useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Icon } from '@iconify/react'
import { Table, TableWrapper } from '@/components/shared'
import { Button } from '@/components/ui'
import { getApiErrorMessage } from '@/utils'
import { StatusPill } from '../components/StatusPill'
import { getMigrationJob, setSheetIncluded, uploadMigrationFile } from '../services'

const MigrationUpload = () => {
  const { jobId = '' } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const fileInput = useRef<HTMLInputElement>(null)
  const roleRef = useRef('')
  const [chosenName, setChosenName] = useState('')
  const job = useQuery({ queryKey: ['migration-job', jobId], queryFn: () => getMigrationJob(jobId) })
  const historical = job.data?.template === 'historical_finance'
  const upload = useMutation({
    mutationFn: ({ file, role }: { file: File; role?: string }) => uploadMigrationFile(jobId, file, role),
    onSuccess: async (file) => {
      await queryClient.invalidateQueries({ queryKey: ['migration-job', jobId] })
      if (file.status === 'rejected') toast.error(file.error || 'Could not read this file')
      else toast.success('File added')
    },
    onError: (error) => toast.error(getApiErrorMessage(error, 'Upload failed')),
  })
  const sheets = (job.data?.files ?? []).flatMap((file) => file.sheets.map((sheet) => ({ file, sheet })))
  const fileName = chosenName || job.data?.files?.[0]?.original_filename || ''

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3 bg-white p-4 custom-shadow-md">
        <div className="flex flex-wrap items-center gap-3">
          <input
            ref={fileInput}
            type="file"
            accept=".xlsx,.csv,text/csv"
            className="sr-only"
            onChange={(event) => {
              const file = event.target.files?.[0]
              if (!file) return
              setChosenName(file.name)
              upload.mutate({ file, role: historical ? roleRef.current : undefined })
              event.target.value = ''
            }}
          />
          {historical ? (
            <>
              <Button className="max-w-fit py-2" loading={upload.isPending && roleRef.current === 'charges'} loadingText="Reading file" onClick={() => { roleRef.current = 'charges'; fileInput.current?.click() }}>
                <Icon icon="hugeicons:upload-01" className="size-4" />
                Charges file
              </Button>
              <Button className="max-w-fit py-2" loading={upload.isPending && roleRef.current === 'payments'} loadingText="Reading file" onClick={() => { roleRef.current = 'payments'; fileInput.current?.click() }}>
                <Icon icon="hugeicons:upload-01" className="size-4" />
                Payments file
              </Button>
            </>
          ) : (
            <Button className="max-w-fit py-2" loading={upload.isPending} loadingText="Reading file" onClick={() => fileInput.current?.click()}>
              <Icon icon="hugeicons:upload-01" className="size-4" />
              Choose file
            </Button>
          )}
          <span className="text-sm text-slate-600">{fileName || 'No file chosen'}</span>
        </div>
        <Button className="max-w-fit py-2" disabled={sheets.length === 0} onClick={() => navigate(`/migration/${jobId}/map`)}>
          Next
        </Button>
      </div>

      {(job.data?.files ?? []).filter((file) => file.error).map((file) => (
        <p key={file.id} className="text-sm text-red-600">{file.original_filename}: {file.error}</p>
      ))}

      <TableWrapper
        isLoading={job.isLoading || upload.isPending}
        isEmpty={!job.isLoading && sheets.length === 0}
        emptyState={{ title: 'No file yet', icon: 'hugeicons:inbox' }}
        variant="card"
      >
        <Table>
          <Table.Head>
            <Table.Row>
              <Table.HeaderCell>Sheet</Table.HeaderCell>
              <Table.HeaderCell>Rows</Table.HeaderCell>
              <Table.HeaderCell>File</Table.HeaderCell>
              <Table.HeaderCell>Include</Table.HeaderCell>
            </Table.Row>
          </Table.Head>
          <Table.Body>
            {sheets.map(({ file, sheet }) => (
              <Table.Row key={sheet.id}>
                <Table.Cell variant="primary">{sheet.sheet_name}</Table.Cell>
                <Table.Cell>{sheet.row_count}</Table.Cell>
                <Table.Cell>
                  {file.role === 'charges' ? 'Charges · ' : file.role === 'payments' ? 'Payments · ' : ''}
                  {file.original_filename} <StatusPill value={file.status} />
                </Table.Cell>
                <Table.Cell>
                  <input
                    type="checkbox"
                    checked={sheet.included}
                    aria-label={`Include ${sheet.sheet_name}`}
                    onChange={async (event) => {
                      await setSheetIncluded(jobId, sheet.id, event.target.checked)
                      await queryClient.invalidateQueries({ queryKey: ['migration-job', jobId] })
                    }}
                  />
                </Table.Cell>
              </Table.Row>
            ))}
          </Table.Body>
        </Table>
      </TableWrapper>
    </div>
  )
}

export default MigrationUpload
