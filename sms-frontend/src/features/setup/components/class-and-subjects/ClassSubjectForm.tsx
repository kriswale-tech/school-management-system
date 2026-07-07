import LevelClassSubjectAccordion from './LevelClassSubjectAccordion'
import type { LevelForSetup } from '../../types'

interface ClassSubjectFormProps {
  levels: LevelForSetup[]
}

const ClassSubjectForm = ({ levels }: ClassSubjectFormProps) => {
  return (
    <div className="space-y-6">
      {levels.map((level) => (
        <LevelClassSubjectAccordion key={level.id ?? level.name} level={level} />
      ))}
    </div>
  )
}

export default ClassSubjectForm
