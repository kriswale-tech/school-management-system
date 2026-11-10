import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { isAxiosError } from 'axios'
import api from '@/lib/api'
import type { PlatformSettings } from '@/features/auth/types'
import { fetchSettings } from '@/features/auth/services'

function errorMessage(error: unknown) {
  if (isAxiosError(error)) {
    const data = error.response?.data as { detail?: string } | undefined
    return data?.detail || 'Request failed'
  }
  return 'Request failed'
}

async function patchSettings(payload: Partial<PlatformSettings>) {
  const { data } = await api.patch<PlatformSettings>('/platform/settings/', payload)
  return data
}

export default function SettingsPage() {
  const queryClient = useQueryClient()
  const settingsQuery = useQuery({
    queryKey: ['platform-settings'],
    queryFn: fetchSettings,
  })

  const mutation = useMutation({
    mutationFn: patchSettings,
    onSuccess: () => {
      toast.success('Settings saved')
      void queryClient.invalidateQueries({ queryKey: ['platform-settings'] })
    },
    onError: (error) => toast.error(errorMessage(error)),
  })

  const settings = settingsQuery.data

  return (
    <div>
      <h1 className="font-[family-name:var(--font-display)] text-3xl font-semibold">
        Platform settings
      </h1>
      <p className="mt-2 text-sm text-[var(--color-ink)]/70">
        Super admins can toggle public registration and billing grace days.
      </p>

      {settingsQuery.isLoading && <p className="mt-6 text-sm">Loading…</p>}
      {settings && (
        <div className="mt-6 space-y-4 rounded-2xl border border-[var(--color-line)] bg-white/90 p-5">
          <label className="flex items-center justify-between gap-4 text-sm">
            <span>
              <span className="block font-medium">Public school registration</span>
              <span className="text-[var(--color-ink)]/60">
                When off, `/accounts/signup/` is blocked.
              </span>
            </span>
            <input
              type="checkbox"
              checked={settings.public_school_registration_enabled}
              onChange={(e) =>
                mutation.mutate({
                  public_school_registration_enabled: e.target.checked,
                })
              }
            />
          </label>
          <label className="block text-sm">
            <span className="mb-1 block font-medium">Subscription grace days</span>
            <input
              type="number"
              min={0}
              defaultValue={settings.subscription_grace_days}
              onBlur={(e) => {
                const value = Number(e.target.value)
                if (!Number.isNaN(value) && value !== settings.subscription_grace_days) {
                  mutation.mutate({ subscription_grace_days: value })
                }
              }}
              className="w-40 rounded-xl border border-[var(--color-line)] bg-[var(--color-panel)] px-3 py-2"
            />
          </label>
        </div>
      )}
    </div>
  )
}
