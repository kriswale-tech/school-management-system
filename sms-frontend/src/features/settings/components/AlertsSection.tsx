import { useEffect, useState } from 'react'
import toast from 'react-hot-toast'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Button, CheckboxField, FormLabel, InputField } from '@/components/ui'
import LoadingSpinner from '@/components/ui/LoadingSpinner'
import { getApiErrorMessage } from '@/utils'
import {
  SCHOOL_ALERTS_QUERY_KEY,
  SCHOOL_SETTINGS_QUERY_KEY,
  getSchoolSettings,
  updateSchoolSettings,
} from '../services'
import type { SchoolSettings } from '../types'
import SettingsSection from './SettingsSection'

const AlertsSection = () => {
  const queryClient = useQueryClient()
  const { data, isLoading } = useQuery({
    queryKey: [SCHOOL_SETTINGS_QUERY_KEY],
    queryFn: getSchoolSettings,
  })
  const [draft, setDraft] = useState<SchoolSettings | null>(null)

  useEffect(() => {
    if (data) setDraft(data)
  }, [data])

  const { mutate: saveAlerts, isPending } = useMutation({
    mutationFn: updateSchoolSettings,
    onSuccess: (saved) => {
      toast.success('Alert settings saved')
      queryClient.setQueryData([SCHOOL_SETTINGS_QUERY_KEY], saved)
      void queryClient.invalidateQueries({ queryKey: [SCHOOL_ALERTS_QUERY_KEY] })
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, 'Unable to save alert settings'))
    },
  })

  return (
    <SettingsSection
      title="Alerts"
      description="In-app alerts for the current term. They appear on the bell for the roles named here. Nothing is emailed or texted."
    >
      {isLoading || !draft ? (
        <LoadingSpinner className="mx-auto" />
      ) : (
        <form
          className="space-y-4"
          onSubmit={(event) => {
            event.preventDefault()
            saveAlerts({
              fees_alert_enabled: draft.fees_alert_enabled,
              fees_alert_threshold: draft.fees_alert_threshold,
              results_alert_enabled: draft.results_alert_enabled,
              enrollments_alert_enabled: draft.enrollments_alert_enabled,
            })
          }}
        >
          <CheckboxField
            checked={draft.fees_alert_enabled}
            onChange={(event) =>
              setDraft({ ...draft, fees_alert_enabled: event.target.checked })
            }
          >
            Outstanding fees for admins and accountants
          </CheckboxField>
          <div className="max-w-xs space-y-2">
            <FormLabel
              label="Fee threshold"
              className="font-normal text-base"
              helperText="Alert when a student owes at least this amount."
            />
            <InputField
              type="number"
              min="0"
              step="0.01"
              value={draft.fees_alert_threshold}
              onChange={(event) =>
                setDraft({ ...draft, fees_alert_threshold: event.target.value })
              }
            />
          </div>
          <CheckboxField
            checked={draft.results_alert_enabled}
            onChange={(event) =>
              setDraft({ ...draft, results_alert_enabled: event.target.checked })
            }
          >
            Unreleased results for admins and class teachers
          </CheckboxField>
          <CheckboxField
            checked={draft.enrollments_alert_enabled}
            onChange={(event) =>
              setDraft({ ...draft, enrollments_alert_enabled: event.target.checked })
            }
          >
            New enrollments for admins
          </CheckboxField>
          <Button type="submit" variant="outline" loading={isPending} loadingText="Saving...">
            Save alerts
          </Button>
        </form>
      )}
    </SettingsSection>
  )
}

export default AlertsSection
