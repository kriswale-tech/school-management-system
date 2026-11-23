import { useEffect, useMemo, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import toast from 'react-hot-toast'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Button } from '@/components/ui'
import InputField from '@/components/ui/InputField'
import { getApiErrorMessage } from '@/utils'
import { applyMappingProfile, getMigrationJob, listMappingProfiles, saveMapping, saveMappingProfile, suggestMapping, validateMigration } from '../services'
import type { FieldMappingInput, TargetField } from '../types'

const fieldClass = 'w-full rounded-lg border border-slate-300 bg-slate-100 px-3 py-2 text-sm text-slate-900'

const DATE_FORMATS = [
  { value: '%d/%m/%Y', label: '31/01/2020' },
  { value: '%m/%d/%Y', label: '01/31/2020' },
  { value: '%Y-%m-%d', label: '2020-01-31' },
]

const MigrationMap = () => {
  const { jobId = '' } = useParams()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const job = useQuery({ queryKey: ['migration-job', jobId], queryFn: () => getMigrationJob(jobId) })
  const sheets = useMemo(
    () => (job.data?.files ?? []).flatMap((file) => file.sheets).filter((sheet) => sheet.included),
    [job.data?.files],
  )
  const [sheetId, setSheetId] = useState('')
  const [profileName, setProfileName] = useState('')
  const [draft, setDraft] = useState<{
    sheetId: string
    mappings: FieldMappingInput[]
    targets: TargetField[]
  } | null>(null)
  const activeId = sheets.some((sheet) => sheet.id === sheetId) ? sheetId : sheets[0]?.id || ''
  const profiles = useQuery({
    queryKey: ['migration-profiles', job.data?.job_type],
    queryFn: () => listMappingProfiles(job.data!.job_type),
    enabled: Boolean(job.data?.job_type),
  })
  const suggestion = useQuery({
    queryKey: ['migration-suggestion', jobId, activeId],
    queryFn: () => suggestMapping(jobId, activeId),
    enabled: Boolean(activeId),
    retry: false,
  })

  useEffect(() => {
    if (!suggestion.error || !suggestion.errorUpdatedAt) return
    toast.error(getApiErrorMessage(suggestion.error, 'Could not suggest columns'))
  }, [suggestion.error, suggestion.errorUpdatedAt])

  const activeSheet = sheets.find((sheet) => sheet.id === activeId)
  const suggestedMappings =
    activeSheet && activeSheet.mappings.length > 0
      ? activeSheet.mappings
      : (suggestion.data?.suggestions ?? [])
  const suggestedTargets = suggestion.data?.targets ?? []
  const mappings = draft?.sheetId === activeId ? draft.mappings : suggestedMappings
  const targets =
    draft?.sheetId === activeId && draft.targets.length > 0 ? draft.targets : suggestedTargets
  const filling = Boolean(activeId) && suggestion.isPending && draft?.sheetId !== activeId

  const setMappings = (
    value: FieldMappingInput[] | ((current: FieldMappingInput[]) => FieldMappingInput[]),
  ) => {
    setDraft((current) => {
      const baseMappings = current?.sheetId === activeId ? current.mappings : suggestedMappings
      const baseTargets =
        current?.sheetId === activeId && current.targets.length > 0
          ? current.targets
          : suggestedTargets
      return {
        sheetId: activeId,
        mappings: typeof value === 'function' ? value(baseMappings) : value,
        targets: baseTargets,
      }
    })
  }

  const suggest = useMutation({
    mutationFn: () => suggestMapping(jobId, activeId),
    onSuccess: (data) => {
      setDraft({ sheetId: activeId, mappings: data.suggestions, targets: data.targets })
    },
    onError: (error) => toast.error(getApiErrorMessage(error, 'Could not suggest columns')),
  })

  const saveAndValidate = useMutation({
    mutationFn: async () => {
      await saveMapping(jobId, activeId, mappings)
      return validateMigration(jobId)
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['migration-job', jobId] })
      navigate(`/migration/${jobId}/values`)
    },
    onError: (error) => toast.error(getApiErrorMessage(error, 'Could not check the file')),
  })

  const mappedTargets = new Set(mappings.filter((item) => item.target_field && !item.ignored).map((item) => item.target_field))
  if (mappedTargets.has('full_name')) {
    mappedTargets.add('first_name')
    mappedTargets.add('last_name')
  }
  const missingRequired = targets.filter((item) => item.required && item.key !== 'full_name' && !mappedTargets.has(item.key))
  const targetOptions = targets.length
    ? targets
    : mappings.filter((item) => item.target_field).map((item) => ({ key: item.target_field, label: item.target_field, required: false }))

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        {sheets.map((sheet) => (
          <button key={sheet.id} type="button" className={`px-3 py-1 text-sm ${sheet.id === activeId ? 'bg-slate-900 text-white' : 'bg-white text-slate-700 custom-shadow-sm'}`} onClick={() => setSheetId(sheet.id)}>
            {sheet.sheet_name}
          </button>
        ))}
        <Button className="max-w-fit py-2" variant="outline" loading={suggest.isPending} disabled={!activeId} onClick={() => suggest.mutate()}>
          Suggest
        </Button>
      </div>

      <div className="space-y-2 bg-white p-4 custom-shadow-md">
        {mappings.length > 0 ? (
          <div className="grid grid-cols-2 gap-2 border-b border-slate-200 pb-2 md:grid-cols-[1fr_1fr_auto_auto]">
            <p className="text-xs font-medium text-slate-500">Your column</p>
            <p className="text-xs font-medium text-slate-500">SCHOOLASST field</p>
          </div>
        ) : null}
        {mappings.map((mapping, index) => (
          <div key={`${mapping.source_column}-${index}`} className="grid items-center gap-2 md:grid-cols-[1fr_1fr_auto_auto]">
            <p className="text-sm font-medium text-slate-900">{mapping.source_column}</p>
            <select
              className={fieldClass}
              value={mapping.ignored ? '' : mapping.target_field}
              onChange={(event) => {
                const value = event.target.value
                const transforms = value === 'full_name'
                  ? [{ step: 'split_name', config: {} }]
                  : value === 'date_of_birth' || value === 'admission_date' || value === 'enrollment_date'
                    ? [{ step: 'date', config: { format: '%d/%m/%Y' } }]
                    : value === 'guardian_phone'
                      ? [{ step: 'phone', config: {} }]
                      : value
                        ? [{ step: 'trim', config: {} }]
                        : []
                setMappings((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, target_field: value, ignored: value === '', suggested: false, transforms } : item))
              }}
            >
              <option value="">Skip</option>
              {targetOptions.filter((item) => item.key).map((item) => (
                <option key={item.key} value={item.key}>{item.label}{item.required ? ' *' : ''}</option>
              ))}
            </select>
            <span className="text-xs text-slate-500">{mapping.ignored ? 'Skipped' : mapping.suggested ? 'Suggested' : 'Chosen'}</span>
            {mapping.transforms[0]?.step === 'date' ? (
              <select
                className={fieldClass}
                value={String(mapping.transforms[0].config.format ?? '%d/%m/%Y')}
                onChange={(event) => setMappings((current) => current.map((item, itemIndex) => itemIndex === index ? { ...item, transforms: [{ step: 'date', config: { format: event.target.value } }] } : item))}
              >
                {DATE_FORMATS.map((format) => <option key={format.value} value={format.value}>{format.label}</option>)}
              </select>
            ) : <span />}
          </div>
        ))}
        {mappings.length === 0 ? (
          <p className="text-sm text-slate-500">
            {sheets.length === 0 ? 'Tick a sheet on the File step.' : filling ? 'Reading columns…' : 'Columns could not be read.'}
          </p>
        ) : null}
      </div>
      {missingRequired.length > 0 ? (
        <p className="text-sm text-red-600">Still needed: {missingRequired.map((item) => item.label).join(', ')}</p>
      ) : null}

      <div className="flex flex-wrap items-center gap-2">
        <InputField wrapperClassName="max-w-xs" className="py-2 text-sm" placeholder="Save as" value={profileName} onChange={(event) => setProfileName(event.target.value)} />
        <Button
          className="max-w-fit py-2"
          variant="outline"
          disabled={!profileName || !job.data}
          onClick={async () => {
            await saveMappingProfile(jobId, activeId, { name: profileName, source_system: job.data?.source_system || '', mappings })
            await queryClient.invalidateQueries({ queryKey: ['migration-profiles'] })
            toast.success('Saved')
          }}
        >
          Save columns
        </Button>
        {(profiles.data ?? []).map((profile) => (
          <Button
            key={profile.id}
            className="max-w-fit py-2"
            variant="ghost"
            onClick={async () => {
              const next = await applyMappingProfile(jobId, activeId, profile.id)
              queryClient.setQueryData(['migration-job', jobId], next)
              const sheet = next.files.flatMap((file) => file.sheets).find((item) => item.id === activeId)
              setMappings(sheet?.mappings ?? [])
            }}
          >
            {profile.name}
          </Button>
        ))}
        <Button className="max-w-fit py-2" loading={saveAndValidate.isPending || filling} disabled={mappings.length === 0} onClick={() => saveAndValidate.mutate()}>
          Next
        </Button>
      </div>
    </div>
  )
}

export default MigrationMap
