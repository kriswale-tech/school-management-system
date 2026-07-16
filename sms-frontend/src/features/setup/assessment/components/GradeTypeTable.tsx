import { useState } from 'react'
import { ChoicePillGroup, type ChoiceItem } from '@/components/shared'
import { FormLabel, InputField } from '@/components/ui'
import type { GradeBand, GradeTemplates, GradeType } from '../types'
import { rowsForGradeType, type GradeRow, type GradeTableState } from '../utils'

const GRADE_TYPE_OPTIONS: ChoiceItem[] = [
  { label: 'Lettered grades (A–F)', value: 'letter' },
  { label: 'Numbered grades (1–9)', value: 'numerical' },
]

type GradeTypeTableProps = {
  gradeTemplates: GradeTemplates
  initialGradeType?: GradeType | null
  initialGradeBands?: GradeBand[] | null
  onChange?: (state: GradeTableState) => void
  className?: string
}

const GradeTypeTable = ({
  gradeTemplates,
  initialGradeType = null,
  initialGradeBands = null,
  onChange,
  className,
}: GradeTypeTableProps) => {
  const [gradeType, setGradeType] = useState<GradeType | null>(initialGradeType)
  const [rows, setRows] = useState<GradeRow[]>(() =>
    initialGradeType
      ? rowsForGradeType(initialGradeType, gradeTemplates, initialGradeBands, initialGradeType)
      : [],
  )

  const emitChange = (nextGradeType: GradeType | null, nextRows: GradeRow[]) => {
    onChange?.({ gradeType: nextGradeType, rows: nextRows })
  }

  const handleGradeTypeChange = (value: string) => {
    const nextType = value as GradeType
    const nextRows = rowsForGradeType(nextType, gradeTemplates, initialGradeBands, initialGradeType)

    setGradeType(nextType)
    setRows(nextRows)
    emitChange(nextType, nextRows)
  }

  const updateRow = (index: number, field: keyof Omit<GradeRow, 'grade'>, value: string) => {
    setRows((current) => {
      const nextRows = current.map((row, rowIndex) =>
        rowIndex === index ? { ...row, [field]: value } : row,
      )
      emitChange(gradeType, nextRows)
      return nextRows
    })
  }

  return (
    <div className={className}>
      <div className="space-y-3">
        <FormLabel label="Grade type" required />
        <p className="text-sm text-slate-500">
          Choose whether results use lettered grades (A–F) or numbered grades (1–9).
        </p>
        <ChoicePillGroup
          name="grade-type"
          items={GRADE_TYPE_OPTIONS}
          value={gradeType}
          onChange={handleGradeTypeChange}
        />
      </div>

      {gradeType ? (
        <div className="mt-5 overflow-x-auto rounded-lg border border-slate-200">
          <table className="min-w-full border-collapse text-left text-sm">
            <thead className="bg-slate-100 text-slate-700">
              <tr>
                <th className="px-4 py-3 font-medium">Grade</th>
                <th className="px-4 py-3 font-medium">Min score</th>
                <th className="px-4 py-3 font-medium">Max score</th>
                <th className="px-4 py-3 font-medium">Remarks</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((row, index) => (
                <tr key={row.grade} className="border-t border-slate-200 bg-white">
                  <td className="px-4 py-3 font-medium text-slate-900">{row.grade}</td>
                  <td className="px-4 py-2">
                    <InputField
                      type="number"
                      min={0}
                      max={100}
                      value={row.min}
                      onChange={(event) => updateRow(index, 'min', event.target.value)}
                      className="rounded-md bg-white py-2"
                      aria-label={`Minimum score for grade ${row.grade}`}
                    />
                  </td>
                  <td className="px-4 py-2">
                    <InputField
                      type="number"
                      min={0}
                      max={100}
                      value={row.max}
                      onChange={(event) => updateRow(index, 'max', event.target.value)}
                      className="rounded-md bg-white py-2"
                      aria-label={`Maximum score for grade ${row.grade}`}
                    />
                  </td>
                  <td className="px-4 py-2">
                    <InputField
                      type="text"
                      value={row.remarks}
                      onChange={(event) => updateRow(index, 'remarks', event.target.value)}
                      className="rounded-md bg-white py-2"
                      aria-label={`Remarks for grade ${row.grade}`}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </div>
  )
}

export default GradeTypeTable
