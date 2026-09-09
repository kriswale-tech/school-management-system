import { useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import SideSlider from '@/components/shared/SideSlider'
import { Button, CheckboxField } from '@/components/ui'
import SearchComponent from '@/components/ui/SearchComponent'
import { getApiErrorMessage } from '@/utils'
import {
  assignSubjectGroupStudents,
  getSubjectGroupCandidates,
} from '../services'
import type { SubjectGroupCandidate } from '../types'

type AssignSubjectGroupStudentsProps = {
  open: boolean
  assignmentId: string
  groupName: string
  onClose: () => void
}

const statusLabel = (candidate: SubjectGroupCandidate) => {
  if (candidate.status === 'unassigned') return 'Unassigned'
  if (candidate.status === 'this_group') return `In ${candidate.current_group_name}`
  return `In ${candidate.current_group_name}`
}

const AssignSubjectGroupStudents = ({
  open,
  assignmentId,
  groupName,
  onClose,
}: AssignSubjectGroupStudentsProps) => {
  const queryClient = useQueryClient()
  const [search, setSearch] = useState('')
  const [selectedIds, setSelectedIds] = useState<string[]>([])

  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['classes', 'teaching-assignment', assignmentId, 'candidates', search],
    queryFn: () => getSubjectGroupCandidates(assignmentId, { search: search || undefined }),
    enabled: open && Boolean(assignmentId),
  })

  const candidates = data?.results ?? []
  const selectableIds = useMemo(
    () => candidates.filter((item) => item.selectable).map((item) => item.id),
    [candidates],
  )

  const { mutate: assignStudents, isPending } = useMutation({
    mutationFn: () => assignSubjectGroupStudents(assignmentId, selectedIds),
    onSuccess: () => {
      toast.success('Students assigned to group')
      void queryClient.invalidateQueries({
        queryKey: ['classes', 'teaching-assignment', assignmentId],
      })
      setSelectedIds([])
      onClose()
    },
    onError: (err) => {
      toast.error(getApiErrorMessage(err, 'Unable to assign students'))
    },
  })

  const toggle = (id: string, selectable: boolean) => {
    if (!selectable) return
    setSelectedIds((current) =>
      current.includes(id) ? current.filter((item) => item !== id) : [...current, id],
    )
  }

  const allSelectableSelected =
    selectableIds.length > 0 && selectableIds.every((id) => selectedIds.includes(id))

  return (
    <SideSlider
      open={open}
      title={`Assign students · ${groupName}`}
      onClose={() => {
        setSelectedIds([])
        setSearch('')
        onClose()
      }}
    >
      <div className="flex h-full flex-col gap-4">
        <p className="text-sm text-slate-600">
          Only unassigned students can be added. Students in another group must be
          unassigned by that group&apos;s teacher first.
        </p>

        <SearchComponent value={search} onChange={setSearch} placeholder="Search students…" />

        {isLoading ? (
          <p className="text-sm text-slate-500 py-4">Loading students…</p>
        ) : isError ? (
          <p className="text-sm text-red-600 py-4" role="alert">
            {getApiErrorMessage(error, 'Unable to load students.')}
          </p>
        ) : candidates.length === 0 ? (
          <p className="text-sm text-slate-500 py-4">No students found for this class.</p>
        ) : (
          <>
            {selectableIds.length > 0 ? (
              <CheckboxField
                checked={allSelectableSelected}
                onChange={() => {
                  setSelectedIds(allSelectableSelected ? [] : selectableIds)
                }}
              >
                Select all unassigned ({selectableIds.length})
              </CheckboxField>
            ) : null}

            <ul className="flex-1 space-y-2 overflow-y-auto pr-1">
              {candidates.map((candidate) => {
                const checked = selectedIds.includes(candidate.id)
                const disabled = !candidate.selectable
                return (
                  <li
                    key={candidate.id}
                    className={`rounded-lg border px-3 py-2 ${
                      disabled ? 'border-slate-100 bg-slate-50' : 'border-slate-200 bg-white'
                    }`}
                  >
                    <CheckboxField
                      checked={checked}
                      disabled={disabled}
                      onChange={() => toggle(candidate.id, candidate.selectable)}
                    >
                      <span className="flex flex-col gap-0.5 text-left">
                        <span className="text-sm font-medium text-slate-900">
                          {candidate.full_name}
                        </span>
                        <span className="text-xs font-normal text-slate-500">
                          {candidate.student_id} · {statusLabel(candidate)}
                        </span>
                      </span>
                    </CheckboxField>
                  </li>
                )
              })}
            </ul>
          </>
        )}

        <div className="mt-auto flex justify-end gap-2 border-t border-slate-100 pt-4">
          <Button
            type="button"
            variant="outline"
            className="py-2 text-sm max-w-fit"
            onClick={() => {
              setSelectedIds([])
              setSearch('')
              onClose()
            }}
          >
            Cancel
          </Button>
          <Button
            type="button"
            className="py-2 text-sm max-w-fit"
            disabled={selectedIds.length === 0 || isPending}
            onClick={() => assignStudents()}
          >
            {isPending ? 'Assigning…' : `Add to ${groupName}`}
          </Button>
        </div>
      </div>
    </SideSlider>
  )
}

export default AssignSubjectGroupStudents
