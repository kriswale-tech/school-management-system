import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { fetchHello, fetchSettings } from '@/features/auth/services'
import { useAuthStore } from '@/features/auth/store'
import { listSchools } from '@/features/schools/services'

export default function DashboardPage() {
  const user = useAuthStore((s) => s.user)

  const helloQuery = useQuery({
    queryKey: ['platform-hello'],
    queryFn: fetchHello,
  })
  const settingsQuery = useQuery({
    queryKey: ['platform-settings'],
    queryFn: fetchSettings,
  })
  const schoolsQuery = useQuery({
    queryKey: ['platform-schools-summary'],
    queryFn: () => listSchools({ page: 1 }),
  })

  return (
    <div>
      <header className="mb-10">
        <p className="font-[family-name:var(--font-display)] text-sm font-semibold tracking-[0.18em] text-[var(--color-accent)] uppercase">
          Overview
        </p>
        <h1 className="mt-2 font-[family-name:var(--font-display)] text-3xl font-semibold tracking-tight">
          Platform overview
        </h1>
        <p className="mt-2 text-[var(--color-ink)]/70">
          Signed in as {user?.full_name || user?.email}. Manage schools and onboarding from here.
        </p>
      </header>

      <div className="grid gap-4 md:grid-cols-2">
        <section className="rounded-2xl border border-[var(--color-line)] bg-white/90 p-5">
          <h2 className="font-[family-name:var(--font-display)] text-lg font-semibold">API</h2>
          {helloQuery.isLoading ? (
            <p className="mt-3 text-sm text-[var(--color-ink)]/60">Loading…</p>
          ) : helloQuery.isError ? (
            <p className="mt-3 text-sm text-red-700">Could not reach platform hello endpoint.</p>
          ) : (
            <dl className="mt-3 space-y-2 text-sm">
              <div className="flex justify-between gap-4">
                <dt className="text-[var(--color-ink)]/60">Name</dt>
                <dd>{helloQuery.data?.name}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-[var(--color-ink)]/60">Version</dt>
                <dd>{helloQuery.data?.version}</dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-[var(--color-ink)]/60">Authenticated</dt>
                <dd>{helloQuery.data?.authenticated ? 'Yes' : 'No'}</dd>
              </div>
            </dl>
          )}
        </section>

        <section className="rounded-2xl border border-[var(--color-line)] bg-white/90 p-5">
          <h2 className="font-[family-name:var(--font-display)] text-lg font-semibold">
            Platform settings
          </h2>
          {settingsQuery.isLoading ? (
            <p className="mt-3 text-sm text-[var(--color-ink)]/60">Loading…</p>
          ) : settingsQuery.isError ? (
            <p className="mt-3 text-sm text-red-700">Could not load settings.</p>
          ) : (
            <dl className="mt-3 space-y-2 text-sm">
              <div className="flex justify-between gap-4">
                <dt className="text-[var(--color-ink)]/60">Public school registration</dt>
                <dd>
                  {settingsQuery.data?.public_school_registration_enabled
                    ? 'Enabled'
                    : 'Disabled'}
                </dd>
              </div>
              <div className="flex justify-between gap-4">
                <dt className="text-[var(--color-ink)]/60">Subscription grace days</dt>
                <dd>{settingsQuery.data?.subscription_grace_days}</dd>
              </div>
            </dl>
          )}
        </section>

        <section className="rounded-2xl border border-[var(--color-line)] bg-white/90 p-5 md:col-span-2">
          <div className="flex items-center justify-between gap-3">
            <h2 className="font-[family-name:var(--font-display)] text-lg font-semibold">
              Schools on platform
            </h2>
            <Link to="/schools" className="text-sm font-medium text-[var(--color-accent)]">
              Open directory →
            </Link>
          </div>
          <p className="mt-3 text-3xl font-semibold">{schoolsQuery.data?.count ?? '—'}</p>
          <p className="mt-1 text-sm text-[var(--color-ink)]/60">
            Create schools, invite admins, and control public registration under Settings.
          </p>
        </section>
      </div>
    </div>
  )
}
