import { useState } from 'react'
import toast from 'react-hot-toast'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Button, CheckboxField, FormLabel, SelectField } from '@/components/ui'
import LoadingSpinner from '@/components/ui/LoadingSpinner'
import { getApiErrorMessage } from '@/utils'
import {
  SCHOOL_SETTINGS_QUERY_KEY,
  getSchoolSettings,
  updateSchoolSettings,
} from '../services'
import type {
  DebtReminderFrequency,
  GuardianAudience,
  GuardianChannel,
  ReportParentNotifyMode,
  SchoolSettings,
} from '../types'
import SettingsSection from './SettingsSection'

const AUDIENCE_OPTIONS = [
  { value: 'primary', label: 'Primary guardian only' },
  { value: 'all', label: 'All linked guardians' },
]

const CHANNEL_OPTIONS = [
  { value: 'both', label: 'SMS and email' },
  { value: 'sms', label: 'SMS only' },
  { value: 'email', label: 'Email only' },
]

const REPORT_MODE_OPTIONS = [
  { value: 'manual', label: 'Staff triggered (default)' },
  { value: 'auto', label: 'Automatic when report PDF is generated' },
]

const DEBT_FREQUENCY_OPTIONS = [
  { value: 'end_of_month', label: 'End of each month (default)' },
  { value: 'weekly', label: 'Weekly (Mondays)' },
  { value: 'biweekly', label: 'Every 2 weeks (Mondays)' },
]

const EVENT_ROWS: {
  enabledKey: keyof SchoolSettings
  channelsKey: keyof SchoolSettings
  label: string
  helper: string
  wired: boolean
}[] = [
  {
    enabledKey: 'guardian_ward_enrolled_enabled',
    channelsKey: 'guardian_ward_enrolled_channels',
    label: 'Ward enrolled',
    helper: 'When a student is added to the school.',
    wired: true,
  },
  {
    enabledKey: 'guardian_payment_receipt_enabled',
    channelsKey: 'guardian_payment_receipt_channels',
    label: 'Payment + receipt link',
    helper: 'When a fee payment is recorded, send a signed receipt link (SMS and/or email).',
    wired: true,
  },
  {
    enabledKey: 'guardian_debt_reminder_enabled',
    channelsKey: 'guardian_debt_reminder_channels',
    label: 'Debt reminders',
    helper:
      'Manual reminders from the Fees desk, plus optional automatic reminders on a schedule.',
    wired: true,
  },
  {
    enabledKey: 'guardian_report_ready_enabled',
    channelsKey: 'guardian_report_ready_channels',
    label: 'Report ready',
    helper: 'Send guardians a signed link when their ward’s report is ready to download.',
    wired: true,
  },
  {
    enabledKey: 'guardian_next_term_fees_enabled',
    channelsKey: 'guardian_next_term_fees_channels',
    label: 'Next-term fees',
    helper:
      'When a fee structure is applied (or a student is billed later), send each guardian their ward’s itemised fee schedule with a signed download link.',
    wired: true,
  },
]

const ParentMessagesSection = () => {
  const queryClient = useQueryClient()
  const { data, isLoading } = useQuery({
    queryKey: [SCHOOL_SETTINGS_QUERY_KEY],
    queryFn: getSchoolSettings,
  })
  const [draftOverride, setDraftOverride] = useState<SchoolSettings | null>(null)
  const draft = draftOverride ?? data ?? null

  const { mutate: saveSettings, isPending } = useMutation({
    mutationFn: updateSchoolSettings,
    onSuccess: (saved) => {
      toast.success('Parent message settings saved')
      setDraftOverride(null)
      queryClient.setQueryData([SCHOOL_SETTINGS_QUERY_KEY], saved)
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, 'Unable to save parent message settings'))
    },
  })

  return (
    <SettingsSection
      title="Parent messages"
      description="Choose which events notify guardians by SMS or email. Messages only go out on channels the school allows, the parent prefers, and for which a phone number or email is on file."
    >
      {isLoading || !draft ? (
        <LoadingSpinner className="mx-auto" />
      ) : (
        <form
          className="space-y-8"
          onSubmit={(event) => {
            event.preventDefault()
            saveSettings({
              guardian_audience: draft.guardian_audience,
              report_parent_notify_mode: draft.report_parent_notify_mode,
              guardian_ward_enrolled_enabled: draft.guardian_ward_enrolled_enabled,
              guardian_ward_enrolled_channels: draft.guardian_ward_enrolled_channels,
              guardian_payment_receipt_enabled: draft.guardian_payment_receipt_enabled,
              guardian_payment_receipt_channels: draft.guardian_payment_receipt_channels,
              guardian_debt_reminder_enabled: draft.guardian_debt_reminder_enabled,
              guardian_debt_reminder_channels: draft.guardian_debt_reminder_channels,
              guardian_debt_reminder_auto_enabled: draft.guardian_debt_reminder_auto_enabled,
              guardian_debt_reminder_frequency: draft.guardian_debt_reminder_frequency,
              guardian_report_ready_enabled: draft.guardian_report_ready_enabled,
              guardian_report_ready_channels: draft.guardian_report_ready_channels,
              guardian_next_term_fees_enabled: draft.guardian_next_term_fees_enabled,
              guardian_next_term_fees_channels: draft.guardian_next_term_fees_channels,
            })
          }}
        >
          <div className="max-w-xs space-y-2">
            <FormLabel label="Default audience" className="font-normal text-base" />
            <SelectField
              options={AUDIENCE_OPTIONS}
              value={draft.guardian_audience}
              onChange={(value) =>
                setDraftOverride({
                  ...draft,
                  guardian_audience: value as GuardianAudience,
                })
              }
            />
            <p className="text-sm text-slate-500">
              Who receives parent messages by default — primary guardian only, or every linked
              guardian.
            </p>
          </div>

          <div className="space-y-4">
            <h3 className="text-sm font-medium text-slate-800">Events</h3>
            {EVENT_ROWS.map((row) => (
              <div
                key={row.enabledKey}
                className="rounded-md border border-slate-200 bg-slate-50/60 p-4 space-y-3"
              >
                <CheckboxField
                  checked={Boolean(draft[row.enabledKey])}
                  onChange={(event) =>
                    setDraftOverride({
                      ...draft,
                      [row.enabledKey]: event.target.checked,
                    })
                  }
                >
                  {row.label}
                  {!row.wired ? (
                    <span className="ml-2 text-xs font-normal text-slate-400">Coming soon</span>
                  ) : null}
                </CheckboxField>
                <p className="text-sm text-slate-500">{row.helper}</p>
                <div className="max-w-xs space-y-2">
                  <FormLabel label="Allowed channels" className="font-normal text-base" />
                  <SelectField
                    options={CHANNEL_OPTIONS}
                    value={String(draft[row.channelsKey])}
                    onChange={(value) =>
                      setDraftOverride({
                        ...draft,
                        [row.channelsKey]: value as GuardianChannel,
                      })
                    }
                    disabled={!draft[row.enabledKey]}
                  />
                </div>

                {row.enabledKey === 'guardian_debt_reminder_enabled' ? (
                  <div className="space-y-3 border-t border-slate-200 pt-3">
                    <CheckboxField
                      checked={Boolean(draft.guardian_debt_reminder_auto_enabled)}
                      disabled={!draft.guardian_debt_reminder_enabled}
                      onChange={(event) =>
                        setDraftOverride({
                          ...draft,
                          guardian_debt_reminder_auto_enabled: event.target.checked,
                        })
                      }
                    >
                      Send automatically on a schedule
                    </CheckboxField>
                    <p className="text-sm text-slate-500">
                      Default is end of each month. Automatic reminders run around 8:00 AM Accra
                      time.
                    </p>
                    <div className="max-w-xs space-y-2">
                      <FormLabel label="Automatic frequency" className="font-normal text-base" />
                      <SelectField
                        options={DEBT_FREQUENCY_OPTIONS}
                        value={draft.guardian_debt_reminder_frequency}
                        onChange={(value) =>
                          setDraftOverride({
                            ...draft,
                            guardian_debt_reminder_frequency: value as DebtReminderFrequency,
                          })
                        }
                        disabled={
                          !draft.guardian_debt_reminder_enabled ||
                          !draft.guardian_debt_reminder_auto_enabled
                        }
                      />
                    </div>
                  </div>
                ) : null}

                {row.enabledKey === 'guardian_report_ready_enabled' ? (
                  <div className="space-y-3 border-t border-slate-200 pt-3">
                    <FormLabel label="When to send" className="font-normal text-base" />
                    <p className="text-sm text-slate-500">
                      Staff can send from Assessment details, or messages go out automatically when
                      the report PDF is generated.
                    </p>
                    <div className="max-w-xs space-y-2">
                      <SelectField
                        options={REPORT_MODE_OPTIONS}
                        value={draft.report_parent_notify_mode}
                        onChange={(value) =>
                          setDraftOverride({
                            ...draft,
                            report_parent_notify_mode: value as ReportParentNotifyMode,
                          })
                        }
                        disabled={!draft.guardian_report_ready_enabled}
                      />
                    </div>
                  </div>
                ) : null}
              </div>
            ))}
          </div>

          <div className="rounded-md border border-dashed border-slate-300 bg-white p-4">
            <h3 className="text-sm font-medium text-slate-800">Messaging credits</h3>
            <p className="mt-1 text-sm text-slate-500">
              Prefer Messaging → Policies for day-to-day parent outreach settings. Credits and
              add-ons are on Billing.
            </p>
          </div>

          <Button type="submit" loading={isPending} loadingText="Saving...">
            Save parent messages
          </Button>
        </form>
      )}
    </SettingsSection>
  )
}

export default ParentMessagesSection
