import { useState } from 'react'
import toast from 'react-hot-toast'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Button, FormLabel } from '@/components/ui'
import LoadingSpinner from '@/components/ui/LoadingSpinner'
import { getApiErrorMessage, mergeClasses } from '@/utils'
import {
  ACADEMIC_CALENDAR_QUERY_KEY,
  createNextAcademicYear,
  getAcademicYearCalendar,
  updateAcademicYearDates,
} from '../services'
import type { AcademicYearCalendar, AcademicYearStatus, CalendarYear, TermKey } from '../types'
import SettingsSection from './SettingsSection'
import { useTransitionWizard } from './TransitionProvider'

const STATUS_LABEL: Record<AcademicYearStatus, string> = {
  past: 'Past',
  current: 'Current',
  upcoming: 'Upcoming',
}

const EMPTY_TERMS: { term: TermKey; name: string }[] = [
  { term: 'first_term', name: 'First Term' },
  { term: 'second_term', name: 'Second Term' },
  { term: 'third_term', name: 'Third Term' },
]

type DraftTerm = {
  term: TermKey
  name: string
  start_date: string
  end_date: string
  can_edit_dates: boolean
  is_active: boolean
  is_next: boolean
  id: string | null
}

const dateInputClassName =
  'w-full rounded-lg border border-slate-300 bg-white p-2 text-sm text-slate-700 outline-none transition focus:border-slate-400 focus:ring-1 focus:ring-slate-400'

const formatDate = (value: string) => {
  const [year, month, day] = value.split('-').map(Number)
  return new Date(year, month - 1, day).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

const draftsFromYear = (year: CalendarYear): DraftTerm[] =>
  year.terms.map((term) => ({
    term: term.term,
    name: term.name,
    start_date: term.start_date ?? '',
    end_date: term.end_date ?? '',
    can_edit_dates: term.can_edit_dates,
    is_active: term.is_active,
    is_next: term.is_next,
    id: term.id,
  }))

const emptyDrafts = (): DraftTerm[] =>
  EMPTY_TERMS.map((term) => ({
    ...term,
    start_date: '',
    end_date: '',
    can_edit_dates: true,
    is_active: false,
    is_next: false,
    id: null,
  }))

const toPayload = (label: string, drafts: DraftTerm[]) => ({
  academic_year: label,
  terms: drafts.map((term) => ({
    term: term.term,
    start_date: term.start_date,
    end_date: term.end_date,
  })),
})

const datesChanged = (year: CalendarYear, drafts: DraftTerm[]) =>
  drafts.some((draft, index) => {
    const stored = year.terms[index]
    return draft.start_date !== (stored?.start_date ?? '') || draft.end_date !== (stored?.end_date ?? '')
  })

const AcademicYearSection = () => {
  const queryClient = useQueryClient()
  const { data, isLoading } = useQuery({
    queryKey: [ACADEMIC_CALENDAR_QUERY_KEY],
    queryFn: getAcademicYearCalendar,
  })
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [adding, setAdding] = useState(false)
  const [drafts, setDrafts] = useState<DraftTerm[]>([])
  const [draftSource, setDraftSource] = useState<string | null>(null)
  const transitionWizard = useTransitionWizard()
  const openWizard = transitionWizard?.openWizard ?? (() => undefined)

  const selectedYear =
    data?.years.find((year) => year.id === selectedId) ??
    data?.years.find((year) => year.is_active) ??
    data?.years[0]

  const draftKey = adding ? `new:${data?.next_year_label ?? ''}` : (selectedYear?.id ?? null)
  if (draftKey !== draftSource) {
    setDraftSource(draftKey)
    setDrafts(adding || !selectedYear ? emptyDrafts() : draftsFromYear(selectedYear))
  }

  const storeCalendar = (calendar: AcademicYearCalendar) => {
    queryClient.setQueryData([ACADEMIC_CALENDAR_QUERY_KEY], calendar)
    void queryClient.invalidateQueries({ queryKey: ['academicYearAndTerm'] })
  }

  const { mutate: saveDates, isPending: isSaving } = useMutation({
    mutationFn: (payload: { yearId?: string; label: string; terms: DraftTerm[] }) => {
      const body = toPayload(payload.label, payload.terms)
      if (payload.yearId) return updateAcademicYearDates(payload.yearId, body)
      return createNextAcademicYear(body)
    },
    onSuccess: (calendar, variables) => {
      storeCalendar(calendar)
      setAdding(false)
      const saved = calendar.years.find((year) => year.academic_year === variables.label)
      if (saved) setSelectedId(saved.id)
      toast.success(variables.yearId ? 'Term dates saved' : 'Next academic year added')
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, 'Unable to save academic year'))
    },
  })

  const updateDraft = (index: number, field: 'start_date' | 'end_date', value: string) => {
    setDrafts((current) =>
      current.map((term, termIndex) => (termIndex === index ? { ...term, [field]: value } : term)),
    )
  }

  const canSaveExisting = Boolean(selectedYear && datesChanged(selectedYear, drafts) && drafts.some((term) => term.can_edit_dates))
  const canSaveNew = drafts.every((term) => term.start_date && term.end_date)

  return (
    <SettingsSection
      title="Academic year and terms"
      description="Open any year to see its terms. The current term is marked. Add the next year while this one is still running, then switch when the school should start using it."
    >
      {isLoading ? <LoadingSpinner className="mx-auto" /> : null}

      {data && !adding ? (
        <div className="space-y-6">
          <div className="flex flex-wrap items-center gap-2">
            {data.years.map((year) => {
              const isSelected = year.id === selectedYear?.id
              return (
                <button
                  key={year.id}
                  type="button"
                  aria-pressed={isSelected}
                  onClick={() => setSelectedId(year.id)}
                  className={mergeClasses(
                    'rounded-full border px-3 py-1.5 text-sm transition',
                    isSelected
                      ? 'border-sky-600 bg-sky-50 text-sky-800'
                      : 'border-slate-200 bg-white text-slate-700 hover:border-slate-300',
                  )}
                >
                  {year.academic_year}
                  <span className="ml-2 text-xs uppercase tracking-wide text-slate-500">
                    {STATUS_LABEL[year.status]}
                  </span>
                </button>
              )
            })}
            {data.next_year_label ? (
              <Button
                type="button"
                variant="outline"
                className="w-auto px-3 py-1.5"
                onClick={() => setAdding(true)}
              >
                Add {data.next_year_label}
              </Button>
            ) : null}
          </div>

          {selectedYear ? (
            <YearTerms
              label={selectedYear.academic_year}
              note={
                selectedYear.status === 'past'
                  ? 'This year is closed. Its dates stay as they were.'
                  : selectedYear.status === 'upcoming'
                    ? 'This year stays inactive until you switch to its first term.'
                    : 'This is the year the school is on.'
              }
              drafts={drafts}
              onChange={updateDraft}
              onSwitch={openWizard}
            />
          ) : (
            <p className="text-sm text-slate-500">Finish school setup to add the first academic year.</p>
          )}

          {selectedYear && drafts.some((term) => term.can_edit_dates) ? (
            <Button
              type="button"
              variant="outline"
              disabled={!canSaveExisting || isSaving}
              loading={isSaving}
              onClick={() =>
                saveDates({
                  yearId: selectedYear.id,
                  label: selectedYear.academic_year,
                  terms: drafts,
                })
              }
            >
              Save dates
            </Button>
          ) : null}
        </div>
      ) : null}

      {data && adding ? (
        <div className="space-y-6">
          <div>
            <h3 className="text-base text-slate-900">{data.next_year_label}</h3>
            <p className="mt-1 text-sm text-slate-500">
              These dates are saved for later. The current term stays in place until you switch.
            </p>
          </div>
          <YearTerms
            label={data.next_year_label ?? ''}
            drafts={drafts}
            onChange={updateDraft}
            onSwitch={openWizard}
          />
          <div className="space-y-3">
            <Button
              type="button"
              variant="outline"
              disabled={!canSaveNew || isSaving || !data.next_year_label}
              loading={isSaving}
              onClick={() =>
                saveDates({
                  label: data.next_year_label ?? '',
                  terms: drafts,
                })
              }
            >
              Save next year
            </Button>
            <Button type="button" variant="ghost" onClick={() => setAdding(false)} disabled={isSaving}>
              Cancel
            </Button>
          </div>
        </div>
      ) : null}

    </SettingsSection>
  )
}

type YearTermsProps = {
  label: string
  note?: string
  drafts: DraftTerm[]
  onChange: (_index: number, _field: 'start_date' | 'end_date', _value: string) => void
  onSwitch: () => void
}

const YearTerms = ({ label, note, drafts, onChange, onSwitch }: YearTermsProps) => {
  return (
    <div className="space-y-4">
      {note ? <p className="text-sm text-slate-500">{note}</p> : null}
      <p className="sr-only">{label}</p>
      {drafts.map((term, index) => (
        <div key={term.term} className="rounded-lg border border-slate-200 p-4">
          <div className="mb-3 flex flex-wrap items-center gap-2">
            <FormLabel label={term.name} className="font-normal text-base" />
            {term.is_active ? (
              <span className="rounded-full bg-sky-100 px-2 py-0.5 text-xs text-sky-800">Current</span>
            ) : null}
          </div>
          {term.can_edit_dates ? (
            <div className="flex gap-4">
              <label className="w-1/2 space-y-2 text-sm text-slate-600">
                Start date
                <input
                  type="date"
                  value={term.start_date}
                  onChange={(event) => onChange(index, 'start_date', event.target.value)}
                  className={dateInputClassName}
                />
              </label>
              <label className="w-1/2 space-y-2 text-sm text-slate-600">
                End date
                <input
                  type="date"
                  value={term.end_date}
                  onChange={(event) => onChange(index, 'end_date', event.target.value)}
                  className={dateInputClassName}
                />
              </label>
            </div>
          ) : (
            <p className="text-sm text-slate-700">
              {term.start_date && term.end_date
                ? `${formatDate(term.start_date)} – ${formatDate(term.end_date)}`
                : 'Dates not set'}
            </p>
          )}
          {term.is_next && term.id ? (
            <Button
              type="button"
              className="mt-4 w-auto"
              variant="outline"
              onClick={onSwitch}
            >
              Open transition
            </Button>
          ) : null}
        </div>
      ))}
    </div>
  )
}

export default AcademicYearSection
