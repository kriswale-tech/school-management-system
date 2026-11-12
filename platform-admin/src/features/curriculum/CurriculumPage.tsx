import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { isAxiosError } from 'axios'
import {
  getCurriculum,
  publishCurriculum,
  saveCurriculumDraft,
  startCurriculumDraft,
  type CurriculumClass,
  type CurriculumLevel,
  type CurriculumSubject,
  type CurriculumVersion,
} from './services'

function errorMessage(error: unknown) {
  if (isAxiosError(error)) {
    const data = error.response?.data as { detail?: string } | undefined
    return data?.detail || 'Request failed'
  }
  return 'Request failed'
}

function newId() {
  return crypto.randomUUID()
}

function fingerprint(version: string, levels: CurriculumLevel[]) {
  return JSON.stringify({ version, levels })
}

type EditorSession = {
  draft: CurriculumVersion
  version: string
  baseline: string
}

type ConfirmRequest = {
  title: string
  body: string
  confirmLabel: string
  dismissLabel: string
  tone: 'danger' | 'neutral'
  onConfirm: () => void
}

const fieldClass =
  'w-full rounded-xl border border-[var(--color-line)] bg-white px-3 py-2 text-sm outline-none focus:border-[var(--color-accent)]'

function ConfirmDialog({
  request,
  onClose,
}: {
  request: ConfirmRequest
  onClose: () => void
}) {
  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="curriculum-confirm-title"
        className="w-full max-w-md rounded-2xl border border-[var(--color-line)] bg-white p-5 shadow-lg"
      >
        <h2
          id="curriculum-confirm-title"
          className="font-[family-name:var(--font-display)] text-lg font-semibold"
        >
          {request.title}
        </h2>
        <p className="mt-2 text-sm text-[var(--color-ink)]/70">{request.body}</p>
        <div className="mt-5 flex justify-end gap-2">
          <button
            type="button"
            autoFocus
            onClick={onClose}
            className="rounded-xl border border-[var(--color-line)] px-3 py-2 text-sm font-medium"
          >
            {request.dismissLabel}
          </button>
          <button
            type="button"
            onClick={() => {
              request.onConfirm()
              onClose()
            }}
            className={
              request.tone === 'danger'
                ? 'rounded-xl bg-red-700 px-3 py-2 text-sm font-semibold text-white'
                : 'rounded-xl bg-[var(--color-accent)] px-3 py-2 text-sm font-semibold text-white'
            }
          >
            {request.confirmLabel}
          </button>
        </div>
      </div>
    </div>
  )
}

function NameChip({
  children,
  tone,
}: {
  children: string
  tone: 'class' | 'subject'
}) {
  const className =
    tone === 'class'
      ? 'inline-flex rounded-lg bg-[var(--color-accent-soft)] px-2.5 py-1 text-sm font-medium text-[var(--color-accent)]'
      : 'inline-flex rounded-full border border-[var(--color-line)] bg-white px-2.5 py-1 text-sm text-[var(--color-ink)]'
  return <span className={className}>{children}</span>
}

function ChipGroup({
  label,
  names,
  tone,
  empty,
}: {
  label: string
  names: string[]
  tone: 'class' | 'subject'
  empty: string
}) {
  return (
    <div>
      <p className="text-xs font-semibold tracking-wide text-[var(--color-ink)]/55 uppercase">{label}</p>
      {names.length === 0 ? (
        <p className="mt-2 text-sm text-[var(--color-ink)]/50">{empty}</p>
      ) : (
        <div className="mt-2 flex flex-wrap gap-2">
          {names.map((name, index) => (
            <NameChip key={`${name}-${index}`} tone={tone}>
              {name}
            </NameChip>
          ))}
        </div>
      )}
    </div>
  )
}

function VersionSection({ version }: { version: CurriculumVersion }) {
  const [open, setOpen] = useState(version.is_active)
  return (
    <section className="rounded-2xl border border-[var(--color-line)] bg-[var(--color-panel)]">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        className="flex w-full cursor-pointer flex-wrap items-center justify-between gap-3 px-5 py-4 text-left"
      >
        <span className="flex flex-wrap items-center gap-2">
          <span className="font-[family-name:var(--font-display)] text-lg font-semibold">
            Version {version.version}
          </span>
          {version.is_active ? (
            <span className="rounded-full bg-[var(--color-accent-soft)] px-2.5 py-0.5 text-xs font-semibold text-[var(--color-accent)]">
              In use
            </span>
          ) : (
            <span className="rounded-full bg-white px-2.5 py-0.5 text-xs font-medium text-[var(--color-ink)]/60">
              Previous
            </span>
          )}
        </span>
        <span className="flex items-center gap-3 text-sm text-[var(--color-ink)]/55">
          <span>
            {version.school_count ?? 0} {(version.school_count ?? 0) === 1 ? 'school' : 'schools'}
          </span>
          <span>{open ? 'Hide' : 'Show'}</span>
        </span>
      </button>
      {open ? (
        <div className="px-5 pb-5">
          <ReadOnlyTree curriculum={version} />
        </div>
      ) : null}
    </section>
  )
}

function VersionHistory({ versions }: { versions: CurriculumVersion[] }) {
  if (versions.length === 0) return null
  return (
    <div className="mb-8 space-y-3">
      <h2 className="font-[family-name:var(--font-display)] text-xl font-semibold">Versions</h2>
      {versions.map((version) => (
        <VersionSection key={version.id} version={version} />
      ))}
    </div>
  )
}

function ReadOnlyTree({ curriculum }: { curriculum: CurriculumVersion }) {
  return (
    <div className="space-y-4">
      {curriculum.levels.map((level) => {
        const subjectCount =
          level.subject_scope === 'level'
            ? level.subjects.length
            : level.classes.reduce((total, classRow) => total + classRow.subjects.length, 0)
        return (
          <section
            key={level.lineage_id}
            className="rounded-2xl border border-[var(--color-line)] bg-white p-5"
          >
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div>
                <h3 className="font-[family-name:var(--font-display)] text-lg font-semibold">
                  {level.name}
                </h3>
                {level.description ? (
                  <p className="mt-1 text-sm text-[var(--color-ink)]/60">{level.description}</p>
                ) : null}
              </div>
              <p className="text-xs font-medium text-[var(--color-ink)]/55">
                {level.subject_scope === 'level' ? 'Subjects shared across classes' : 'Subjects set per class'}
                {' · '}
                {level.classes.length} {level.classes.length === 1 ? 'class' : 'classes'}
                {' · '}
                {subjectCount} {subjectCount === 1 ? 'subject' : 'subjects'}
              </p>
            </div>

            {level.subject_scope === 'level' ? (
              <div className="mt-4 space-y-4">
                <ChipGroup
                  label="Classes"
                  tone="class"
                  names={level.classes.map((classRow) => classRow.name)}
                  empty="No classes on this level."
                />
                <ChipGroup
                  label="Subjects"
                  tone="subject"
                  names={level.subjects.map((subject) => subject.name)}
                  empty="No subjects on this level."
                />
              </div>
            ) : (
              <div className="mt-4 space-y-3">
                {level.classes.length === 0 ? (
                  <p className="text-sm text-[var(--color-ink)]/50">No classes on this level.</p>
                ) : (
                  level.classes.map((classRow) => (
                    <div key={classRow.lineage_id} className="rounded-xl bg-[var(--color-panel)] p-3">
                      <p className="text-sm font-semibold">{classRow.name}</p>
                      <div className="mt-2">
                        <ChipGroup
                          label="Subjects"
                          tone="subject"
                          names={classRow.subjects.map((subject) => subject.name)}
                          empty="No subjects for this class."
                        />
                      </div>
                    </div>
                  ))
                )}
              </div>
            )}
          </section>
        )
      })}
    </div>
  )
}

function SubjectEditor({
  subjects,
  onChange,
}: {
  subjects: CurriculumSubject[]
  onChange: (subjects: CurriculumSubject[]) => void
}) {
  return (
    <div className="mt-3">
      <p className="text-xs font-semibold tracking-wide text-[var(--color-ink)]/55 uppercase">Subjects</p>
      <div className="mt-2 flex flex-wrap gap-2">
        {subjects.map((subject) => (
          <span
            key={subject.lineage_id}
            className="inline-flex items-center gap-1 rounded-full border border-[var(--color-line)] bg-white py-1 pr-1 pl-3 text-sm"
          >
            <input
              value={subject.name}
              onChange={(event) =>
                onChange(
                  subjects.map((row) =>
                    row.lineage_id === subject.lineage_id ? { ...row, name: event.target.value } : row,
                  ),
                )
              }
              style={{ width: `${Math.max(subject.name.length, 8)}ch` }}
              className="max-w-56 bg-transparent outline-none"
              aria-label="Subject name"
              placeholder="Subject"
            />
            <button
              type="button"
              onClick={() => onChange(subjects.filter((row) => row.lineage_id !== subject.lineage_id))}
              aria-label={`Remove ${subject.name || 'subject'}`}
              className="flex h-6 w-6 items-center justify-center rounded-full text-[var(--color-ink)]/50 hover:bg-red-50 hover:text-red-700"
            >
              ×
            </button>
          </span>
        ))}
        <button
          type="button"
          className="rounded-full border border-dashed border-[var(--color-line)] px-3 py-1 text-sm text-[var(--color-ink)]/70 hover:border-[var(--color-accent)] hover:text-[var(--color-accent)]"
          onClick={() => onChange([...subjects, { lineage_id: newId(), name: '' }])}
        >
          Add subject
        </button>
      </div>
    </div>
  )
}

function LevelEditor({
  level,
  onChange,
  onRemoveLevel,
  onRemoveClass,
}: {
  level: CurriculumLevel
  onChange: (level: CurriculumLevel) => void
  onRemoveLevel: () => void
  onRemoveClass: (classRow: CurriculumClass) => void
}) {
  function updateClass(lineageId: string, next: CurriculumClass) {
    onChange({
      ...level,
      classes: level.classes.map((row) => (row.lineage_id === lineageId ? next : row)),
    })
  }

  return (
    <section className="rounded-2xl border border-[var(--color-line)] bg-white p-5">
      <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_14rem]">
        <label className="text-sm">
          <span className="mb-1 block font-medium">Level</span>
          <input
            value={level.name}
            placeholder="Level name"
            onChange={(event) => onChange({ ...level, name: event.target.value })}
            className={fieldClass}
          />
        </label>
        <label className="text-sm">
          <span className="mb-1 block font-medium">Subjects apply</span>
          <select
            value={level.subject_scope}
            onChange={(event) =>
              onChange({
                ...level,
                subject_scope: event.target.value as CurriculumLevel['subject_scope'],
              })
            }
            className={fieldClass}
          >
            <option value="level">Across the level</option>
            <option value="class">Per class</option>
          </select>
        </label>
      </div>
      <label className="mt-3 block text-sm">
        <span className="mb-1 block font-medium">Description</span>
        <input
          value={level.description}
          placeholder="Short description, optional"
          onChange={(event) => onChange({ ...level, description: event.target.value })}
          className={fieldClass}
        />
      </label>

      <div className="mt-5">
        <p className="text-xs font-semibold tracking-wide text-[var(--color-ink)]/55 uppercase">Classes</p>
        <div className="mt-2 space-y-3">
          {level.classes.map((classRow) => (
            <div key={classRow.lineage_id} className="rounded-xl bg-[var(--color-panel)] p-3">
              <div className="flex gap-2">
                <input
                  value={classRow.name}
                  placeholder="Class name"
                  onChange={(event) => updateClass(classRow.lineage_id, { ...classRow, name: event.target.value })}
                  className={fieldClass}
                  aria-label="Class name"
                />
                <button
                  type="button"
                  className="shrink-0 rounded-xl border border-red-200 bg-white px-3 py-2 text-sm font-medium text-red-700"
                  onClick={() => onRemoveClass(classRow)}
                >
                  Remove class
                </button>
              </div>
              {level.subject_scope === 'class' ? (
                <SubjectEditor
                  subjects={classRow.subjects}
                  onChange={(subjects) => updateClass(classRow.lineage_id, { ...classRow, subjects })}
                />
              ) : null}
            </div>
          ))}
          <button
            type="button"
            className="rounded-xl border border-dashed border-[var(--color-line)] px-3 py-2 text-sm text-[var(--color-ink)]/70 hover:border-[var(--color-accent)] hover:text-[var(--color-accent)]"
            onClick={() =>
              onChange({
                ...level,
                classes: [
                  ...level.classes,
                  { lineage_id: newId(), name: '', order: level.classes.length + 1, subjects: [] },
                ],
              })
            }
          >
            Add class
          </button>
        </div>
      </div>

      {level.subject_scope === 'level' ? (
        <SubjectEditor
          subjects={level.subjects}
          onChange={(subjects) => onChange({ ...level, subjects })}
        />
      ) : null}

      <div className="mt-5 border-t border-[var(--color-line)] pt-4">
        <button
          type="button"
          onClick={onRemoveLevel}
          className="text-sm font-medium text-red-700 hover:underline"
        >
          Remove level
        </button>
      </div>
    </section>
  )
}

export default function CurriculumPage() {
  const queryClient = useQueryClient()
  const overviewQuery = useQuery({
    queryKey: ['platform-curriculum'],
    queryFn: getCurriculum,
  })
  const overview = overviewQuery.data
  const [session, setSession] = useState<EditorSession | null>(null)
  const [confirm, setConfirm] = useState<ConfirmRequest | null>(null)

  function beginEditing(next: CurriculumVersion) {
    setSession({
      draft: next,
      version: next.version,
      baseline: fingerprint(next.version, next.levels),
    })
  }

  function updateDraft(updater: (current: CurriculumVersion) => CurriculumVersion) {
    setSession((current) => (current ? { ...current, draft: updater(current.draft) } : current))
  }

  const dirty = session
    ? fingerprint(session.version, session.draft.levels) !== session.baseline
    : false

  const startMutation = useMutation({
    mutationFn: startCurriculumDraft,
    onSuccess: (next) => {
      beginEditing(next)
      void queryClient.invalidateQueries({ queryKey: ['platform-curriculum'] })
    },
    onError: (error) => toast.error(errorMessage(error)),
  })

  const saveMutation = useMutation({
    mutationFn: () => {
      if (!session) throw new Error('No draft')
      return saveCurriculumDraft(session.draft.id, session.version, session.draft.levels)
    },
    onSuccess: (saved) => {
      beginEditing(saved)
      toast.success('Draft saved')
      void queryClient.invalidateQueries({ queryKey: ['platform-curriculum'] })
    },
    onError: (error) => toast.error(errorMessage(error)),
  })

  const publishMutation = useMutation({
    mutationFn: async () => {
      if (!session) throw new Error('No draft')
      const saved = await saveCurriculumDraft(session.draft.id, session.version, session.draft.levels)
      return publishCurriculum(saved.id)
    },
    onSuccess: (result) => {
      setSession(null)
      toast.success(
        `Published ${result.curriculum.version}. ${result.schools_alerted} schools will see an alert until they adopt.`,
      )
      void queryClient.invalidateQueries({ queryKey: ['platform-curriculum'] })
    },
    onError: (error) => toast.error(errorMessage(error)),
  })

  const pending = startMutation.isPending || saveMutation.isPending || publishMutation.isPending

  function requestCancel() {
    if (!session) return
    if (!dirty) {
      setSession(null)
      return
    }
    setConfirm({
      title: 'Leave without saving?',
      body: 'Your unsaved changes will be dropped. The last saved draft stays, so you can continue it later.',
      confirmLabel: 'Leave',
      dismissLabel: 'Keep editing',
      tone: 'neutral',
      onConfirm: () => setSession(null),
    })
  }

  function requestRemoveLevel(level: CurriculumLevel) {
    const name = level.name.trim() || 'this level'
    setConfirm({
      title: `Remove ${name}?`,
      body: `${name} and its classes and subjects will leave this draft. Schools keep the live curriculum until you publish.`,
      confirmLabel: 'Remove level',
      dismissLabel: 'Keep level',
      tone: 'danger',
      onConfirm: () =>
        updateDraft((current) => ({
          ...current,
          levels: current.levels.filter((row) => row.lineage_id !== level.lineage_id),
        })),
    })
  }

  function requestRemoveClass(level: CurriculumLevel, classRow: CurriculumClass) {
    const name = classRow.name.trim() || 'this class'
    setConfirm({
      title: `Remove ${name}?`,
      body: `${name} will leave ${level.name.trim() || 'this level'}. Schools keep the live curriculum until you publish.`,
      confirmLabel: 'Remove class',
      dismissLabel: 'Keep class',
      tone: 'danger',
      onConfirm: () =>
        updateDraft((current) => ({
          ...current,
          levels: current.levels.map((row) =>
            row.lineage_id === level.lineage_id
              ? { ...row, classes: row.classes.filter((item) => item.lineage_id !== classRow.lineage_id) }
              : row,
          ),
        })),
    })
  }

  return (
    <div>
      {confirm ? <ConfirmDialog request={confirm} onClose={() => setConfirm(null)} /> : null}

      <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <p className="text-sm font-semibold tracking-[0.18em] text-[var(--color-accent)] uppercase">
            Curriculum
          </p>
          <h1 className="mt-2 font-[family-name:var(--font-display)] text-3xl font-semibold">
            Ghana standard
          </h1>
          <p className="mt-2 max-w-2xl text-sm text-[var(--color-ink)]/70">
            This is the curriculum new schools copy. Publishing a version alerts every school
            still on an older one. Their classes change only when that school adopts it.
          </p>
        </div>
        {!session && overview?.active && !overview.draft ? (
          <button
            type="button"
            onClick={() => startMutation.mutate()}
            disabled={pending}
            className="rounded-xl bg-[var(--color-accent)] px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
          >
            New version
          </button>
        ) : null}
      </header>

      {overviewQuery.isLoading ? <p className="text-sm text-[var(--color-ink)]/60">Loading…</p> : null}
      {overviewQuery.isError ? (
        <p className="text-sm text-red-700">Could not load the curriculum.</p>
      ) : null}

      {!session && overview?.draft ? (
        <section className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-[var(--color-line)] bg-white p-5">
          <div>
            <p className="text-xs font-semibold tracking-wide text-[var(--color-accent)] uppercase">
              Draft in progress
            </p>
            <h2 className="mt-1 font-[family-name:var(--font-display)] text-xl font-semibold">
              Version {overview.draft.version}
            </h2>
            <p className="mt-1 text-sm text-[var(--color-ink)]/65">
              Saved and not published. Schools stay on the live version until you publish.
            </p>
          </div>
          <button
            type="button"
            onClick={() => beginEditing(overview.draft as CurriculumVersion)}
            className="rounded-xl bg-[var(--color-accent)] px-4 py-2 text-sm font-semibold text-white"
          >
            Continue editing
          </button>
        </section>
      ) : null}

      {session ? (
        <form
          className="mb-8 space-y-4"
          onSubmit={(event) => {
            event.preventDefault()
            saveMutation.mutate()
          }}
        >
          <div className="flex flex-wrap items-end justify-between gap-3 rounded-2xl border border-[var(--color-line)] bg-white p-5">
            <label className="text-sm">
              <span className="mb-1 block font-medium">Version</span>
              <input
                value={session.version}
                onChange={(event) =>
                  setSession((current) =>
                    current ? { ...current, version: event.target.value } : current,
                  )
                }
                className={`${fieldClass} w-40`}
              />
              <span className="mt-2 block text-xs text-[var(--color-ink)]/55">
                {dirty ? 'Unsaved changes' : 'All changes saved'}
              </span>
            </label>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={requestCancel}
                disabled={pending}
                className="rounded-xl border border-[var(--color-line)] px-4 py-2 text-sm font-semibold disabled:opacity-60"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={pending}
                className="rounded-xl border border-[var(--color-line)] px-4 py-2 text-sm font-semibold disabled:opacity-60"
              >
                {saveMutation.isPending ? 'Saving…' : 'Save draft'}
              </button>
              <button
                type="button"
                disabled={pending}
                onClick={() => publishMutation.mutate()}
                className="rounded-xl bg-[var(--color-accent)] px-4 py-2 text-sm font-semibold text-white disabled:opacity-60"
              >
                {publishMutation.isPending ? 'Publishing…' : 'Publish'}
              </button>
            </div>
          </div>

          {session.draft.levels.map((level) => (
            <LevelEditor
              key={level.lineage_id}
              level={level}
              onChange={(next) =>
                updateDraft((current) => ({
                  ...current,
                  levels: current.levels.map((row) =>
                    row.lineage_id === level.lineage_id ? next : row,
                  ),
                }))
              }
              onRemoveLevel={() => requestRemoveLevel(level)}
              onRemoveClass={(classRow) => requestRemoveClass(level, classRow)}
            />
          ))}
          <button
            type="button"
            className="rounded-xl border border-dashed border-[var(--color-line)] px-4 py-2 text-sm text-[var(--color-ink)]/70 hover:border-[var(--color-accent)] hover:text-[var(--color-accent)]"
            onClick={() =>
              updateDraft((current) => ({
                ...current,
                levels: [
                  ...current.levels,
                  {
                    lineage_id: newId(),
                    name: '',
                    description: '',
                    order: current.levels.length + 1,
                    subject_scope: 'level',
                    allows_custom_classes: false,
                    classes: [],
                    subjects: [],
                  },
                ],
              }))
            }
          >
            Add level
          </button>
        </form>
      ) : null}

      {!session && overview ? <VersionHistory versions={overview.versions} /> : null}

      {overview && overview.schools_behind.length > 0 ? (
        <section className="rounded-2xl border border-amber-200 bg-amber-50 p-5">
          <h2 className="font-semibold">Schools still on an older version</h2>
          <p className="mt-1 text-sm text-amber-950">
            Each of these schools has an alert. Open a school to adopt for them, or they can adopt
            from Manage classes.
          </p>
          <ul className="mt-3 space-y-2 text-sm">
            {overview.schools_behind.map((school) => (
              <li key={school.id} className="flex flex-wrap items-baseline gap-2">
                <Link
                  to={`/schools/${school.id}`}
                  className="font-medium text-[var(--color-accent)] hover:underline"
                >
                  {school.name}
                </Link>
                <span className="rounded-full bg-white px-2 py-0.5 text-xs text-amber-950">
                  Version {school.version}
                </span>
              </li>
            ))}
          </ul>
        </section>
      ) : null}
    </div>
  )
}
