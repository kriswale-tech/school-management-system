import { useState, type FormEvent } from 'react'
import { Navigate, useNavigate } from 'react-router-dom'
import toast from 'react-hot-toast'
import { isAxiosError } from 'axios'
import { login, verifyMfa } from './services'
import { useAuthStore } from './store'

function errorMessage(error: unknown) {
  if (isAxiosError(error)) {
    const data = error.response?.data as { detail?: string; message?: string } | undefined
    return data?.detail || data?.message || 'Login failed'
  }
  return 'Login failed'
}

export default function LoginPage() {
  const navigate = useNavigate()
  const user = useAuthStore((s) => s.user)
  const setUser = useAuthStore((s) => s.setUser)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [mfaToken, setMfaToken] = useState<string | null>(null)
  const [mfaCode, setMfaCode] = useState('')
  const [submitting, setSubmitting] = useState(false)

  if (user) {
    return <Navigate to="/" replace />
  }

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setSubmitting(true)
    try {
      if (mfaToken) {
        const result = await verifyMfa(mfaCode, mfaToken)
        setUser(result.user)
        toast.success('Signed in')
        navigate('/', { replace: true })
        return
      }

      const result = await login(email.trim(), password)
      if (result.mfa_required && result.mfa_token) {
        setMfaToken(result.mfa_token)
        toast('Enter your authenticator code')
        return
      }
      setUser(result.user)
      toast.success('Signed in')
      navigate('/', { replace: true })
    } catch (error) {
      toast.error(errorMessage(error))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="mx-auto flex min-h-screen w-full max-w-md flex-col justify-center px-6 py-12">
      <div className="mb-10">
        <p className="font-[family-name:var(--font-display)] text-sm font-semibold tracking-[0.18em] text-[var(--color-accent)] uppercase">
          SCHOOLASST
        </p>
        <h1 className="mt-3 font-[family-name:var(--font-display)] text-3xl font-semibold tracking-tight">
          Platform admin
        </h1>
        <p className="mt-2 text-[var(--color-ink)]/70">
          Sign in with your platform email and password.
        </p>
      </div>

      <form
        onSubmit={onSubmit}
        className="rounded-2xl border border-[var(--color-line)] bg-white/90 p-6 shadow-[0_20px_50px_rgba(18,32,51,0.08)]"
      >
        {!mfaToken ? (
          <>
            <label className="mb-4 block">
              <span className="mb-1.5 block text-sm font-medium">Email</span>
              <input
                type="email"
                autoComplete="username"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full rounded-xl border border-[var(--color-line)] bg-[var(--color-panel)] px-3 py-2.5 outline-none focus:border-[var(--color-accent)]"
              />
            </label>
            <label className="mb-6 block">
              <span className="mb-1.5 block text-sm font-medium">Password</span>
              <input
                type="password"
                autoComplete="current-password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full rounded-xl border border-[var(--color-line)] bg-[var(--color-panel)] px-3 py-2.5 outline-none focus:border-[var(--color-accent)]"
              />
            </label>
          </>
        ) : (
          <label className="mb-6 block">
            <span className="mb-1.5 block text-sm font-medium">Authenticator code</span>
            <input
              type="text"
              inputMode="numeric"
              autoComplete="one-time-code"
              required
              value={mfaCode}
              onChange={(e) => setMfaCode(e.target.value)}
              className="w-full rounded-xl border border-[var(--color-line)] bg-[var(--color-panel)] px-3 py-2.5 outline-none focus:border-[var(--color-accent)]"
            />
          </label>
        )}

        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-xl bg-[var(--color-accent)] px-4 py-2.5 font-semibold text-white transition hover:brightness-105 disabled:opacity-60"
        >
          {submitting ? 'Please wait…' : mfaToken ? 'Verify MFA' : 'Sign in'}
        </button>
      </form>
    </div>
  )
}
