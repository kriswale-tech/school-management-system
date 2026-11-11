import { useEffect, useState, type FormEvent } from 'react'

export type InviteAdminPayload = {
  first_name: string
  last_name: string
  phone_number: string
  email: string
}

type Props = {
  open: boolean
  pending: boolean
  onClose: () => void
  onInvite: (payload: InviteAdminPayload) => void
}

const EMPTY: InviteAdminPayload = {
  first_name: '',
  last_name: '',
  phone_number: '',
  email: '',
}

export default function InviteAdminModal({ open, pending, onClose, onInvite }: Props) {
  const [form, setForm] = useState<InviteAdminPayload>(EMPTY)

  useEffect(() => {
    if (!open) setForm(EMPTY)
  }, [open])

  useEffect(() => {
    if (!open) return
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape' && !pending) onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose, pending])

  if (!open) return null

  function submit(event: FormEvent) {
    event.preventDefault()
    if (pending) return
    onInvite(form)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4">
      <form
        onSubmit={submit}
        className="w-full max-w-md rounded-2xl border border-[var(--color-line)] bg-white p-5 shadow-lg"
      >
        <h2 className="font-[family-name:var(--font-display)] text-lg font-semibold">
          Invite admin
        </h2>
        <p className="mt-1 text-sm text-[var(--color-ink)]/70">
          They receive a link to join this school as an admin.
        </p>
        <div className="mt-4 space-y-3">
          {(
            [
              ['first_name', 'First name', true],
              ['last_name', 'Last name', false],
              ['phone_number', 'Phone', true],
              ['email', 'Email', true],
            ] as const
          ).map(([key, label, required]) => (
            <label key={key} className="block text-sm">
              <span className="mb-1 block font-medium">{label}</span>
              <input
                required={required}
                type={key === 'email' ? 'email' : 'text'}
                value={form[key]}
                onChange={(event) =>
                  setForm((prev) => ({ ...prev, [key]: event.target.value }))
                }
                className="w-full rounded-xl border border-[var(--color-line)] bg-[var(--color-panel)] px-3 py-2"
              />
            </label>
          ))}
        </div>
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
            disabled={pending}
            className="rounded-xl bg-[var(--color-accent)] px-3 py-2 text-sm font-semibold text-white disabled:opacity-60"
          >
            {pending ? 'Sending…' : 'Send invite'}
          </button>
        </div>
      </form>
    </div>
  )
}
