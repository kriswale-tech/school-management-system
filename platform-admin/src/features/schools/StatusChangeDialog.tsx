import { useEffect, useState, type FormEvent } from 'react'
import type { SchoolStatus } from './types'

export function statusActionLabel(status: SchoolStatus) {
  if (status === 'active') return 'Activate'
  if (status === 'pending') return 'Mark pending'
  if (status === 'suspended') return 'Suspend'
  return 'Archive'
}

function statusHelp(status: SchoolStatus) {
  if (status === 'active') return 'The school can sign in and work again.'
  if (status === 'pending') return 'The school goes back to pending until it is activated.'
  if (status === 'suspended') return 'The school loses access until it is activated again.'
  return 'The school stays in the directory and can be activated again later.'
}

type Props = {
  schoolName: string
  status: SchoolStatus
  pending: boolean
  onClose: () => void
  onConfirm: (reason: string) => void
}

export default function StatusChangeDialog({
  schoolName,
  status,
  pending,
  onClose,
  onConfirm,
}: Props) {
  const [reason, setReason] = useState('')
  const label = statusActionLabel(status)
  const ready = reason.trim().length > 0 && !pending

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape' && !pending) onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose, pending])

  function submit(event: FormEvent) {
    event.preventDefault()
    const cleaned = reason.trim()
    if (!cleaned || pending) return
    onConfirm(cleaned)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <form
        onSubmit={submit}
        className="w-full max-w-md rounded-2xl border border-[var(--color-line)] bg-white p-5 shadow-lg"
      >
        <h2 className="font-[family-name:var(--font-display)] text-lg font-semibold">
          {label} {schoolName}
        </h2>
        <p className="mt-2 text-sm text-[var(--color-ink)]/70">{statusHelp(status)}</p>
        <label className="mt-4 block text-sm">
          <span className="mb-1 block font-medium">Reason</span>
          <textarea
            required
            autoFocus
            rows={3}
            maxLength={500}
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            placeholder="Why is this status changing?"
            className="w-full rounded-xl border border-[var(--color-line)] bg-[var(--color-panel)] px-3 py-2"
          />
        </label>
        <div className="mt-5 flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            disabled={pending}
            className="rounded-xl border border-[var(--color-line)] px-3 py-2 text-sm disabled:opacity-50"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={!ready}
            className="rounded-xl bg-[var(--color-accent)] px-3 py-2 text-sm font-semibold text-white disabled:opacity-60"
          >
            {pending ? 'Saving…' : label}
          </button>
        </div>
      </form>
    </div>
  )
}
