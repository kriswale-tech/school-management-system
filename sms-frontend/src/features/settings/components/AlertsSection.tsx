import { useState } from 'react'
import toast from 'react-hot-toast'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Button, FormLabel, InputField, ToggleField } from '@/components/ui'
import LoadingSpinner from '@/components/ui/LoadingSpinner'
import { getApiErrorMessage } from '@/utils'
import {
  SCHOOL_ALERTS_QUERY_KEY,
  SCHOOL_SETTINGS_QUERY_KEY,
  TRANSITION_STATUS_QUERY_KEY,
  getSchoolSettings,
  updateSchoolSettings,
} from '../services'
import { ADMIN_DASHBOARD_QUERY_KEY } from '@/features/dashboard/utils'
import type { SchoolSettings } from '../types'
import SettingsSection from './SettingsSection'

const AlertsSection = () => {
  const queryClient = useQueryClient()
  const { data, isLoading } = useQuery({
    queryKey: [SCHOOL_SETTINGS_QUERY_KEY],
    queryFn: getSchoolSettings,
  })
  const [draftOverride, setDraftOverride] = useState<SchoolSettings | null>(null)
  const draft = draftOverride ?? data ?? null

  const { mutate: saveAlerts, isPending } = useMutation({
    mutationFn: updateSchoolSettings,
    onSuccess: (saved) => {
      toast.success('Alert settings saved')
      setDraftOverride(null)
      queryClient.setQueryData([SCHOOL_SETTINGS_QUERY_KEY], saved)
      void queryClient.invalidateQueries({ queryKey: [SCHOOL_ALERTS_QUERY_KEY] })
      void queryClient.invalidateQueries({ queryKey: [TRANSITION_STATUS_QUERY_KEY] })
      void queryClient.invalidateQueries({ queryKey: [ADMIN_DASHBOARD_QUERY_KEY] })
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
          onSubmit={(event) => {
            event.preventDefault()
            saveAlerts({
              fees_alert_enabled: draft.fees_alert_enabled,
              fees_alert_threshold: draft.fees_alert_threshold,
              results_alert_enabled: draft.results_alert_enabled,
              enrollments_alert_enabled: draft.enrollments_alert_enabled,
              guardians_alert_enabled: draft.guardians_alert_enabled,
              transition_popup_enabled: draft.transition_popup_enabled,
              curriculum_alert_enabled: draft.curriculum_alert_enabled,
            })
          }}
        >
          <div className="divide-y divide-slate-200 border-y border-slate-200">
            <div className="space-y-4 py-5">
              <ToggleField
                checked={draft.fees_alert_enabled}
                onChange={(event) =>
                  setDraftOverride({ ...draft, fees_alert_enabled: event.target.checked })
                }
              >
                Outstanding fees for admins and accountants
              </ToggleField>
              <div className="max-w-xs space-y-2 pl-0.5">
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
                    setDraftOverride({ ...draft, fees_alert_threshold: event.target.value })
                  }
                />
              </div>
            </div>
            <div className="py-5">
              <ToggleField
                checked={draft.results_alert_enabled}
                onChange={(event) =>
                  setDraftOverride({ ...draft, results_alert_enabled: event.target.checked })
                }
              >
                Unreleased results for admins and class teachers
              </ToggleField>
            </div>
            <div className="py-5">
              <ToggleField
                checked={draft.enrollments_alert_enabled}
                onChange={(event) =>
                  setDraftOverride({ ...draft, enrollments_alert_enabled: event.target.checked })
                }
              >
                New enrollments for admins and staff
              </ToggleField>
            </div>
            <div className="py-5">
              <ToggleField
                checked={draft.guardians_alert_enabled}
                onChange={(event) =>
                  setDraftOverride({ ...draft, guardians_alert_enabled: event.target.checked })
                }
              >
                Missing guardians for admins and staff
              </ToggleField>
            </div>
            <div className="py-5">
              <ToggleField
                checked={draft.transition_popup_enabled}
                onChange={(event) =>
                  setDraftOverride({ ...draft, transition_popup_enabled: event.target.checked })
                }
              >
                Popup on the dashboard while opening the next term still needs action
              </ToggleField>
            </div>
            <div className="py-5">
              <ToggleField
                checked={draft.curriculum_alert_enabled}
                onChange={(event) =>
                  setDraftOverride({ ...draft, curriculum_alert_enabled: event.target.checked })
                }
              >
                Curriculum update on the bell and dashboard until the school adopts it for the next term
              </ToggleField>
            </div>
          </div>
          <div className="pt-5">
            <Button type="submit" variant="outline" loading={isPending} loadingText="Saving...">
              Save alerts
            </Button>
          </div>
        </form>
      )}
    </SettingsSection>
  )
}

export default AlertsSection
