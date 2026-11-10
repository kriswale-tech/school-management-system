import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Button, FormLabel, SelectField, ToggleField } from '@/components/ui'
import LoadingSpinner from '@/components/ui/LoadingSpinner'
import { getApiErrorMessage } from '@/utils'
import {
  SCHOOL_SETTINGS_QUERY_KEY,
  getSchoolSettings,
  updateSchoolSettings,
} from '@/features/settings/services'
import type {
  DebtReminderFrequency,
  GuardianAudience,
  GuardianChannel,
  ReportParentNotifyMode,
  SchoolSettings,
} from '@/features/settings/types'
import SettingsSection from '@/features/settings/components/SettingsSection'
import { Link } from 'react-router-dom'
import {
  getMessageTemplates,
  previewMessageTemplate,
  updateMessageTemplate,
} from '../services'
import type { MessageTemplate, MessageTemplatePreview } from '../types'

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
  eventType: string
  label: string
  helper: string
}[] = [
  {
    enabledKey: 'guardian_ward_enrolled_enabled',
    channelsKey: 'guardian_ward_enrolled_channels',
    eventType: 'ward_enrolled',
    label: 'Ward enrolled',
    helper: 'When a student is added to the school.',
  },
  {
    enabledKey: 'guardian_payment_receipt_enabled',
    channelsKey: 'guardian_payment_receipt_channels',
    eventType: 'payment_receipt',
    label: 'Payment + receipt link',
    helper: 'When a fee payment is recorded, send a signed receipt link (SMS and/or email).',
  },
  {
    enabledKey: 'guardian_debt_reminder_enabled',
    channelsKey: 'guardian_debt_reminder_channels',
    eventType: 'debt_reminder',
    label: 'Debt reminders',
    helper:
      'Manual reminders from the Fees desk, plus optional automatic reminders on a schedule.',
  },
  {
    enabledKey: 'guardian_report_ready_enabled',
    channelsKey: 'guardian_report_ready_channels',
    eventType: 'report_ready',
    label: 'Report ready',
    helper: 'Send guardians a signed link when their ward’s report is ready to download.',
  },
  {
    enabledKey: 'guardian_next_term_fees_enabled',
    channelsKey: 'guardian_next_term_fees_channels',
    eventType: 'next_term_fees',
    label: 'Next-term fees',
    helper:
      'When a fee structure is applied (or a student is billed later), send each guardian their ward’s itemised fee schedule with a signed download link.',
  },
]

const TEMPLATES_QUERY_KEY = 'messaging-templates'
const textareaClassName =
  'w-full rounded-lg border border-slate-300 bg-slate-100 px-3 py-3 text-base text-slate-900 outline-none transition placeholder:text-slate-400 focus:border-slate-400 focus:ring-1 focus:ring-slate-400 disabled:cursor-not-allowed disabled:bg-slate-50'

type TemplateDraft = {
  sms_body: string
  sms_body_all_time: string
  email_subject: string
  email_text: string
}

function EventTemplateEditor({ template }: { template: MessageTemplate }) {
  const queryClient = useQueryClient()
  const [open, setOpen] = useState(false)
  const [channelTab, setChannelTab] = useState<'sms' | 'email'>('sms')
  const [allTime, setAllTime] = useState(false)
  const [draft, setDraft] = useState<TemplateDraft>({
    sms_body: template.sms_body,
    sms_body_all_time: template.sms_body_all_time,
    email_subject: template.email_subject,
    email_text: template.email_text,
  })
  const [preview, setPreview] = useState<MessageTemplatePreview | null>(null)

  useEffect(() => {
    setDraft({
      sms_body: template.sms_body,
      sms_body_all_time: template.sms_body_all_time,
      email_subject: template.email_subject,
      email_text: template.email_text,
    })
  }, [template])

  const { mutate: saveTemplate, isPending: saving } = useMutation({
    mutationFn: updateMessageTemplate,
    onSuccess: (rows) => {
      toast.success('Message template saved')
      queryClient.setQueryData([TEMPLATES_QUERY_KEY], rows)
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, 'Unable to save template'))
    },
  })

  const { mutate: runPreview, isPending: previewing } = useMutation({
    mutationFn: previewMessageTemplate,
    onSuccess: setPreview,
    onError: (error) => {
      toast.error(getApiErrorMessage(error, 'Unable to preview'))
    },
  })

  const isDebt = template.event_type === 'debt_reminder'
  const smsValue = isDebt && allTime ? draft.sms_body_all_time : draft.sms_body
  const smsIsCustom =
    isDebt && allTime ? template.sms_body_all_time_is_custom : template.sms_body_is_custom

  return (
    <div className="border-t border-slate-200 pt-3 space-y-3">
      <button
        type="button"
        className="text-sm font-medium text-sky-700 hover:underline"
        onClick={() => setOpen((value) => !value)}
      >
        {open ? 'Hide message template' : 'Edit message template'}
      </button>

      {open ? (
        <div className="space-y-4 rounded-md border border-slate-200 bg-white p-3">
          <div className="flex flex-wrap gap-2">
            {(['sms', 'email'] as const).map((tab) => (
              <button
                key={tab}
                type="button"
                onClick={() => {
                  setChannelTab(tab)
                  setPreview(null)
                }}
                className={
                  channelTab === tab
                    ? 'rounded-md bg-slate-800 px-3 py-1.5 text-sm text-white'
                    : 'rounded-md bg-slate-100 px-3 py-1.5 text-sm text-slate-700'
                }
              >
                {tab === 'sms' ? 'SMS' : 'Email'}
              </button>
            ))}
          </div>

          <p className="text-xs text-slate-500">
            Placeholders:{' '}
            {template.placeholders.map((row) => `{{${row.key}}}`).join(', ')}
          </p>

          {channelTab === 'sms' ? (
            <div className="space-y-3">
              {isDebt ? (
                <ToggleField checked={allTime} onChange={(event) => setAllTime(event.target.checked)}>
                  Edit all-time debt reminder SMS
                </ToggleField>
              ) : null}
              <div className="space-y-1.5">
                <FormLabel label="SMS body" className="font-normal text-base" />
                <p className="rounded-md border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-600">
                  Fixed prefix: <span className="font-medium">{template.sms_prefix_example}</span>
                </p>
                <textarea
                  rows={4}
                  className={textareaClassName}
                  value={smsValue}
                  onChange={(event) =>
                    setDraft((prev) =>
                      isDebt && allTime
                        ? { ...prev, sms_body_all_time: event.target.value }
                        : { ...prev, sms_body: event.target.value },
                    )
                  }
                />
                <p className="text-xs text-slate-500">
                  {smsIsCustom ? 'Custom copy' : 'Using system default'} · SMS credits = segments
                  after the prefix is applied.
                </p>
              </div>
            </div>
          ) : (
            <div className="space-y-3">
              <div className="space-y-1.5">
                <FormLabel label="Email subject" className="font-normal text-base" />
                <input
                  className={textareaClassName}
                  value={draft.email_subject}
                  onChange={(event) =>
                    setDraft((prev) => ({ ...prev, email_subject: event.target.value }))
                  }
                />
              </div>
              <div className="space-y-1.5">
                <FormLabel label="Email body (text)" className="font-normal text-base" />
                <textarea
                  rows={6}
                  className={textareaClassName}
                  value={draft.email_text}
                  onChange={(event) =>
                    setDraft((prev) => ({ ...prev, email_text: event.target.value }))
                  }
                />
                <p className="text-xs text-slate-500">
                  Leave on system default HTML styling unless you save custom text. Saving text
                  replaces the branded HTML email with a plain styled version.
                </p>
              </div>
            </div>
          )}

          <div className="flex flex-wrap items-center gap-2">
            <Button
              type="button"
              className="w-auto"
              loading={previewing}
              loadingText="Previewing..."
              onClick={() =>
                runPreview({
                  event_type: template.event_type,
                  channel: channelTab,
                  sms_body: draft.sms_body,
                  sms_body_all_time: draft.sms_body_all_time,
                  email_subject: draft.email_subject,
                  email_text: draft.email_text,
                  all_time: isDebt && allTime,
                })
              }
            >
              Preview
            </Button>
            <Button
              type="button"
              className="w-auto"
              loading={saving}
              loadingText="Saving..."
              onClick={() =>
                saveTemplate({
                  event_type: template.event_type,
                  ...(channelTab === 'sms'
                    ? isDebt && allTime
                      ? { sms_body_all_time: draft.sms_body_all_time }
                      : { sms_body: draft.sms_body }
                    : {
                        email_subject: draft.email_subject,
                        email_text: draft.email_text,
                      }),
                })
              }
            >
              Save template
            </Button>
            <Button
              type="button"
              variant="outline"
              className="w-auto"
              loading={saving}
              loadingText="Restoring..."
              onClick={() =>
                saveTemplate({
                  event_type: template.event_type,
                  restore:
                    channelTab === 'sms'
                      ? isDebt && allTime
                        ? ['sms_body_all_time']
                        : ['sms_body']
                      : ['email_subject', 'email_text', 'email_html'],
                })
              }
            >
              Restore default
            </Button>
          </div>

          {preview ? (
            <div className="space-y-2 rounded-md border border-slate-200 bg-slate-50 p-3">
              <h4 className="text-sm font-medium text-slate-800">Preview</h4>
              {preview.channel === 'email' && preview.rendered_subject ? (
                <p className="text-sm text-slate-700">
                  <span className="font-medium">Subject:</span> {preview.rendered_subject}
                </p>
              ) : null}
              <pre className="whitespace-pre-wrap break-words text-sm text-slate-700">
                {preview.rendered}
              </pre>
              {preview.sms ? (
                <dl className="grid grid-cols-2 gap-2 text-sm text-slate-600 sm:grid-cols-4">
                  <div>
                    <dt className="text-xs uppercase tracking-wide text-slate-400">Characters</dt>
                    <dd className="font-medium text-slate-800">{preview.sms.characters}</dd>
                  </div>
                  <div>
                    <dt className="text-xs uppercase tracking-wide text-slate-400">Encoding</dt>
                    <dd className="font-medium text-slate-800">{preview.sms.encoding}</dd>
                  </div>
                  <div>
                    <dt className="text-xs uppercase tracking-wide text-slate-400">Segments</dt>
                    <dd className="font-medium text-slate-800">{preview.sms.segments}</dd>
                  </div>
                  <div>
                    <dt className="text-xs uppercase tracking-wide text-slate-400">Credits / recipient</dt>
                    <dd className="font-medium text-slate-800">
                      {preview.sms.credits_per_recipient}
                    </dd>
                  </div>
                </dl>
              ) : null}
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  )
}

const ParentMessagesSection = () => {
  const queryClient = useQueryClient()
  const { data, isLoading } = useQuery({
    queryKey: [SCHOOL_SETTINGS_QUERY_KEY],
    queryFn: getSchoolSettings,
  })
  const { data: templates = [], isLoading: templatesLoading } = useQuery({
    queryKey: [TEMPLATES_QUERY_KEY],
    queryFn: getMessageTemplates,
  })
  const [draftOverride, setDraftOverride] = useState<SchoolSettings | null>(null)
  const draft = draftOverride ?? data ?? null
  const templatesByType = Object.fromEntries(templates.map((row) => [row.event_type, row]))

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
      description="Choose which events notify guardians by SMS or email, and edit the copy sent for each event. Messages only go out on channels the school allows, the parent prefers, and for which a phone number or email is on file."
    >
      {isLoading || templatesLoading || !draft ? (
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
            {EVENT_ROWS.map((row) => {
              const template = templatesByType[row.eventType]
              return (
                <div
                  key={row.enabledKey}
                  className="rounded-md border border-slate-200 bg-slate-50/60 p-4 space-y-3"
                >
                  <ToggleField
                    checked={Boolean(draft[row.enabledKey])}
                    onChange={(event) =>
                      setDraftOverride({
                        ...draft,
                        [row.enabledKey]: event.target.checked,
                      })
                    }
                  >
                    {row.label}
                  </ToggleField>
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
                      <ToggleField
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
                      </ToggleField>
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
                      <div className="max-w-md space-y-2">
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

                  {template ? <EventTemplateEditor template={template} /> : null}
                </div>
              )
            })}
          </div>

          <div className="rounded-md border border-dashed border-slate-300 bg-white p-4">
            <h3 className="text-sm font-medium text-slate-800">Messaging credits</h3>
            <p className="mt-1 text-sm text-slate-500">
              Balances and SMS/email add-ons live on the Billing page. Delivery attempts are logged
              under Messaging → History.
            </p>
            <Link
              to="/settings/billing"
              className="mt-3 inline-block text-sm font-medium text-sky-700 hover:underline"
            >
              Open Billing →
            </Link>
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
