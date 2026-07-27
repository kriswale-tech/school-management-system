import { mergeClasses } from '@/utils'
import { Table } from '../../data-table'
import { DEFAULT_PREVIEW_HINT } from '../constants'
import type { BulkImportRowStatus, PreviewResultsProps } from '../types'

const statusClasses: Record<BulkImportRowStatus, string> = {
  valid: 'bg-green-100 text-green-700',
  error: 'bg-red-100 text-red-700',
  warning: 'bg-amber-100 text-amber-700',
}

const statusLabels: Record<BulkImportRowStatus, string> = {
  valid: 'Valid',
  error: 'Error',
  warning: 'Warning',
}

const PreviewResults = ({ preview, hint = DEFAULT_PREVIEW_HINT }: PreviewResultsProps) => {
  const { summary, rows } = preview

  const summaryItems = [
    { label: 'Total rows', value: summary.rows_total },
    { label: 'Valid', value: summary.rows_valid },
    { label: 'Errors', value: summary.rows_with_errors },
    { label: 'Warnings', value: summary.rows_with_warnings },
  ]

  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-500">{hint}</p>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {summaryItems.map((item) => (
          <div
            key={item.label}
            className="rounded-lg border border-slate-200 bg-white px-4 py-3 text-center"
          >
            <p className="text-lg font-semibold text-slate-900">{item.value}</p>
            <p className="text-xs text-slate-500">{item.label}</p>
          </div>
        ))}
      </div>

      <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
        <Table>
          <Table.Head>
            <Table.Row>
              <Table.HeaderCell>Row</Table.HeaderCell>
              <Table.HeaderCell>Status</Table.HeaderCell>
              <Table.HeaderCell>Details</Table.HeaderCell>
            </Table.Row>
          </Table.Head>
          <Table.Body>
            {rows.map((row) => (
              <Table.Row key={row.row_number}>
                <Table.Cell className="whitespace-nowrap font-medium text-slate-900">
                  {row.row_number}
                </Table.Cell>
                <Table.Cell className="whitespace-nowrap">
                  <span
                    className={mergeClasses(
                      'inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium capitalize',
                      statusClasses[row.status],
                    )}
                  >
                    {statusLabels[row.status]}
                  </span>
                </Table.Cell>
                <Table.Cell className="text-slate-600">
                  {row.messages.length > 0 ? (
                    <ul className="list-disc space-y-1 pl-4">
                      {row.messages.map((message) => (
                        <li key={message}>{message}</li>
                      ))}
                    </ul>
                  ) : (
                    <span className="text-slate-400">No issues</span>
                  )}
                </Table.Cell>
              </Table.Row>
            ))}
          </Table.Body>
        </Table>
      </div>
    </div>
  )
}

export default PreviewResults
