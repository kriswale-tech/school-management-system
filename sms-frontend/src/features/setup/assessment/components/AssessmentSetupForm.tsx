import toast from 'react-hot-toast'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Button, FormLabel, InputField } from '@/components/ui'
import { ChoicePillGroup, type ChoiceItem } from '@/components/shared'
import { getApiErrorMessage } from '@/utils'
import { saveLevelConfig } from '../services'
import type { AssessmentConfigResponse, Level, ResultType } from '../types'
import {
  buildLevelConfigPayload,
  getLevelFormValues,
  parseConfigWeight,
  rowsForGradeType,
  validateLevelForm,
  type GradeTableState,
} from '../utils'
import GradeTypeTable from './GradeTypeTable'

const RESULT_FORMAT_OPTIONS: ChoiceItem[] = [
  {
    label: 'Grade only',
    value: 'grade',
  },
  {
    label: 'Position only',
    value: 'position',
  },
  {
    label: 'Both Grade and Position',
    value: 'grade_and_position',
  },
]

const showsGradeTypeTable = (resultFormat: ResultType | null) =>
  resultFormat === 'grade' || resultFormat === 'grade_and_position'

type AssessmentSetupFormProps = {
  config: AssessmentConfigResponse
  onComplete: () => void
  isCompleting: boolean
}

const AssessmentSetupForm = ({ config, onComplete, isCompleting }: AssessmentSetupFormProps) => {
  const sortedLevels = [...config.levels].sort((a, b) => a.level_order - b.level_order)

  return (
    <div className="space-y-6">
      {sortedLevels.map((level) => (
        <AssessmentSetupFormItem
          key={level.level_id}
          level={level}
          gradeTemplates={config.grade_templates}
        />
      ))}

      <Button type="button" variant="outline" onClick={onComplete} loading={isCompleting}>
        Proceed to Next Step
      </Button>
    </div>
  )
}

export default AssessmentSetupForm

type AssessmentSetupFormItemProps = {
  level: Level
  gradeTemplates: AssessmentConfigResponse['grade_templates']
}

const AssessmentSetupFormItem = ({ level, gradeTemplates }: AssessmentSetupFormItemProps) => {
  const queryClient = useQueryClient()
  const { config } = level

  const [continuousAssessmentWeight, setContinuousAssessmentWeight] = useState(
    parseConfigWeight(config?.continuous_assessment_weight),
  )
  const [examWeight, setExamWeight] = useState(parseConfigWeight(config?.exam_weight))
  const [resultFormat, setResultFormat] = useState<ResultType | null>(config?.result_type ?? null)
  const [gradeTable, setGradeTable] = useState<GradeTableState>(() => {
    if (config?.grade_type) {
      return {
        gradeType: config.grade_type,
        rows: rowsForGradeType(
          config.grade_type,
          gradeTemplates,
          config.grade_bands,
          config.grade_type,
        ),
      }
    }

    return { gradeType: null, rows: [] }
  })

  const { mutate: saveConfig, isPending: isSaving } = useMutation({
    mutationFn: (payload: Parameters<typeof saveLevelConfig>[1]) =>
      saveLevelConfig(level.level_id, payload),
    onSuccess: () => {
      toast.success(`${level.level_name} saved`)
      void queryClient.invalidateQueries({ queryKey: ['assessmentConfig'] })
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, `Unable to save ${level.level_name}`))
    },
  })

  const handleSave = () => {
    const validationError = validateLevelForm({
      continuousAssessmentWeight,
      examWeight,
      resultType: resultFormat,
      gradeTable,
    })

    if (validationError) {
      toast.error(validationError)
      return
    }

    const formValues = getLevelFormValues(
      resultFormat,
      continuousAssessmentWeight,
      examWeight,
      gradeTable,
      config,
    )

    if (!formValues) {
      toast.error('Please complete all required fields')
      return
    }

    saveConfig(buildLevelConfigPayload(formValues))
  }

  return (
    <div className="form-field-wrapper space-y-5">
      <h3 className="text-lg text-slate-900">{level.level_name}</h3>

      <div className="flex gap-4 items-center justify-between">
        <div className="w-1/2 space-y-2">
          <FormLabel label="Continuous Assessment (%)" required />
          <InputField
            type="number"
            placeholder="Enter the percentage of continuous assessment"
            min={0}
            max={100}
            value={continuousAssessmentWeight}
            onChange={(event) => setContinuousAssessmentWeight(event.target.value)}
            className="rounded-none bg-white py-3"
          />
        </div>
        <div className="w-1/2 space-y-2">
          <FormLabel label="Exams (%)" required />
          <InputField
            type="number"
            placeholder="Enter the percentage of exams"
            min={0}
            max={100}
            value={examWeight}
            onChange={(event) => setExamWeight(event.target.value)}
            className="rounded-none bg-white py-3"
          />
        </div>
      </div>

      <div className="space-y-4">
        <p>Please select the format you want the end of semester results to be displayed in.</p>

        <ChoicePillGroup
          name={`result-format-${level.level_id}`}
          items={RESULT_FORMAT_OPTIONS}
          value={resultFormat}
          onChange={(value) => setResultFormat(value as ResultType)}
        />

        {showsGradeTypeTable(resultFormat) ? (
          <GradeTypeTable
            gradeTemplates={gradeTemplates}
            initialGradeType={config?.grade_type ?? null}
            initialGradeBands={config?.grade_bands ?? null}
            onChange={setGradeTable}
          />
        ) : null}
      </div>

      <div className="flex justify-end pt-2">
        <Button type="button" className="w-fit" onClick={handleSave} loading={isSaving}>
          Save
        </Button>
      </div>
    </div>
  )
}
