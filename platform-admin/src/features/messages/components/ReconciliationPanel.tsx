import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import {
  Badge,
  badgeToneFor,
  Field,
  GhostButton,
  Pagination,
  Panel,
  PrimaryButton,
  SelectInput,
  TableState,
  TableWrap,
  Td,
  Th,
  Thead,
  TextInput,
} from './ui'
import { errorMessage, formatDateTime, titleCase } from '../lib'
import {
  listReconciliationItems,
  listReconciliationRuns,
  reconcileProvider,
  resolveReconciliationItem,
} from '../services'
import { useMessagesAccess } from '../permissions'
import type { Provider, ReconciliationResolution } from '../types'

const RESOLUTION_TONE: Record<ReconciliationResolution, 'warn' | 'success' | 'info' | 'neutral'> = {
  open: 'warn',
  accepted: 'success',
  adjusted: 'info',
  ignored: 'neutral',
}

export default function ReconciliationPanel() {
  const queryClient = useQueryClient()
  const { can } = useMessagesAccess()
  const canTrigger = can('reconciliation.trigger')
  const canResolve = can('reconciliation.resolve')

  const [providerFilter, setProviderFilter] = useState<Provider | ''>('')
  const [runsPage, setRunsPage] = useState(1)
  const [openRunId, setOpenRunId] = useState<string | null>(null)
  const [resolution, setResolution] = useState<Record<string, { value: string; note: string }>>({})

  const runsQuery = useQuery({
    queryKey: ['platform-messages-recon-runs', providerFilter, runsPage],
    queryFn: () =>
      listReconciliationRuns({
        provider: providerFilter || undefined,
        page: runsPage,
      }),
    retry: false,
  })

  const itemsQuery = useQuery({
    queryKey: ['platform-messages-recon-items', openRunId],
    queryFn: () => listReconciliationItems(openRunId as string),
    enabled: Boolean(openRunId),
    retry: false,
  })

  const triggerMutation = useMutation({
    mutationFn: (provider: Provider) => reconcileProvider(provider),
    onSuccess: (run) => {
      toast.success('Reconciliation run started')
      setOpenRunId(run?.id ?? null)
      void queryClient.invalidateQueries({ queryKey: ['platform-messages-recon-runs'] })
    },
    onError: (error) => toast.error(errorMessage(error)),
  })

  const resolveMutation = useMutation({
    mutationFn: ({
      runId,
      itemId,
      payload,
    }: {
      runId: string
      itemId: string
      payload: { resolution: 'accepted' | 'adjusted' | 'ignored'; resolution_note: string }
    }) => resolveReconciliationItem(runId, itemId, payload),
    onSuccess: () => {
      toast.success('Discrepancy resolved')
      void queryClient.invalidateQueries({ queryKey: ['platform-messages-recon-items'] })
      void queryClient.invalidateQueries({ queryKey: ['platform-messages-recon-runs'] })
    },
    onError: (error) => toast.error(errorMessage(error)),
  })

  const runs = runsQuery.data?.results ?? []
  const items = itemsQuery.data?.results ?? []

  return (
    <Panel
      title="Provider reconciliation"
      description="Compares internal delivery records against provider reports. Resolving a discrepancy appends a new typed ledger entry — it never edits history."
      actions={
        <>
          <SelectInput
            value={providerFilter}
            onChange={(e) => {
              setProviderFilter(e.target.value as Provider | '')
              setRunsPage(1)
            }}
            className="w-auto"
          >
            <option value="">All providers</option>
            <option value="arkesel">Arkesel</option>
            <option value="ses">Amazon SES</option>
            <option value="resend">Resend (legacy)</option>
          </SelectInput>
          {canTrigger && (
            <>
              <GhostButton
                disabled={triggerMutation.isPending}
                onClick={() => triggerMutation.mutate('arkesel')}
              >
                Reconcile Arkesel
              </GhostButton>
              <GhostButton
                disabled={triggerMutation.isPending}
                onClick={() => triggerMutation.mutate('ses')}
              >
                Reconcile SES
              </GhostButton>
            </>
          )}
        </>
      }
      footnote="Reconciliation never silently modifies historical ledger entries or balances. Corrections are new manual_adjust or reversal entries referencing the item."
    >
      <TableWrap>
        <Thead>
          <tr>
            <Th>Run</Th>
            <Th>Window</Th>
            <Th>Status</Th>
            <Th align="right">Matched</Th>
            <Th align="right">Unmatched</Th>
            <Th align="right">Discrepancies</Th>
            <Th>Triggered by</Th>
            <Th>Items</Th>
          </tr>
        </Thead>
        <tbody>
          <TableState
            colSpan={8}
            isLoading={runsQuery.isLoading}
            isError={runsQuery.isError}
            error={runsQuery.error}
            isEmpty={runs.length === 0}
            emptyMessage="No reconciliation runs recorded yet."
          />
          {runs.map((run) => (
            <tr key={run.id} className="border-b border-[var(--color-line)] last:border-0">
              <Td>
                <span className="font-medium capitalize">{run.provider}</span>
                <span className="block text-xs text-[var(--color-ink)]/50 uppercase">
                  {run.channel}
                </span>
              </Td>
              <Td>
                <span className="text-xs">
                  {formatDateTime(run.window_start)} → {formatDateTime(run.window_end)}
                </span>
              </Td>
              <Td>
                <Badge tone={run.error_detail ? 'danger' : badgeToneFor(run.status)}>
                  {titleCase(run.status)}
                </Badge>
              </Td>
              <Td align="right">{run.matched_count}</Td>
              <Td align="right">{run.unmatched_count}</Td>
              <Td align="right">{run.discrepancy_count}</Td>
              <Td>
                <span className="text-[var(--color-ink)]/70">{run.triggered_by_name || '—'}</span>
                <span className="block text-xs text-[var(--color-ink)]/50">
                  {formatDateTime(run.finished_at ?? run.started_at)}
                </span>
              </Td>
              <Td>
                <GhostButton
                  onClick={() => setOpenRunId(openRunId === run.id ? null : run.id)}
                >
                  {openRunId === run.id ? 'Hide' : 'Investigate'}
                </GhostButton>
              </Td>
            </tr>
          ))}
        </tbody>
      </TableWrap>
      <Pagination
        count={runsQuery.data?.count ?? 0}
        page={runsPage}
        onPage={setRunsPage}
      />

      {openRunId && (
        <div className="mt-5 rounded-2xl border border-[var(--color-line)] bg-[var(--color-panel)] p-4">
          <h4 className="mb-3 text-sm font-semibold">Discrepancies in this run</h4>
          <TableWrap>
            <Thead>
              <tr>
                <Th>Discrepancy</Th>
                <Th>Internal record</Th>
                <Th>Provider message</Th>
                <Th>Resolution</Th>
                {canResolve && <Th>Resolve</Th>}
              </tr>
            </Thead>
            <tbody>
              <TableState
                colSpan={canResolve ? 5 : 4}
                isLoading={itemsQuery.isLoading}
                isError={itemsQuery.isError}
                error={itemsQuery.error}
                isEmpty={items.length === 0}
                emptyMessage="This run found no discrepancies."
              />
              {items.map((item) => {
                const draft = resolution[item.id] ?? { value: 'accepted', note: '' }
                return (
                  <tr key={item.id} className="border-b border-[var(--color-line)] last:border-0">
                    <Td>{titleCase(item.discrepancy_type)}</Td>
                    <Td>
                      <span className="text-xs text-[var(--color-ink)]/70">
                        {item.internal_delivery_type || '—'}
                      </span>
                      <span className="block font-mono text-xs text-[var(--color-ink)]/50">
                        {item.internal_delivery_id || '—'}
                      </span>
                    </Td>
                    <Td>
                      <span className="font-mono text-xs">{item.provider_message_id || '—'}</span>
                    </Td>
                    <Td>
                      <Badge tone={RESOLUTION_TONE[item.resolution] ?? 'neutral'}>
                        {titleCase(item.resolution)}
                      </Badge>
                      {item.resolution_note && (
                        <span className="mt-1 block text-xs text-[var(--color-ink)]/55">
                          {item.resolution_note}
                        </span>
                      )}
                      {item.resolved_by_name && (
                        <span className="block text-xs text-[var(--color-ink)]/50">
                          {item.resolved_by_name} · {formatDateTime(item.resolved_at)}
                        </span>
                      )}
                    </Td>
                    {canResolve && (
                      <Td>
                        {item.resolution === 'open' ? (
                          <div className="flex min-w-[260px] flex-col gap-2">
                            <Field label="Outcome">
                              <SelectInput
                                value={draft.value}
                                onChange={(e) =>
                                  setResolution((prev) => ({
                                    ...prev,
                                    [item.id]: { ...draft, value: e.target.value },
                                  }))
                                }
                              >
                                <option value="accepted">Accepted</option>
                                <option value="adjusted">Adjusted (new ledger entry)</option>
                                <option value="ignored">Ignored</option>
                              </SelectInput>
                            </Field>
                            <Field label="Note">
                              <TextInput
                                value={draft.note}
                                placeholder="Why this outcome"
                                onChange={(e) =>
                                  setResolution((prev) => ({
                                    ...prev,
                                    [item.id]: { ...draft, note: e.target.value },
                                  }))
                                }
                              />
                            </Field>
                            <PrimaryButton
                              disabled={resolveMutation.isPending || !draft.note.trim()}
                              onClick={() =>
                                resolveMutation.mutate({
                                  runId: openRunId,
                                  itemId: item.id,
                                  payload: {
                                    resolution: draft.value as 'accepted' | 'adjusted' | 'ignored',
                                    resolution_note: draft.note.trim(),
                                  },
                                })
                              }
                            >
                              Resolve
                            </PrimaryButton>
                          </div>
                        ) : (
                          <span className="text-xs text-[var(--color-ink)]/55">Closed</span>
                        )}
                      </Td>
                    )}
                  </tr>
                )
              })}
            </tbody>
          </TableWrap>
        </div>
      )}
    </Panel>
  )
}
