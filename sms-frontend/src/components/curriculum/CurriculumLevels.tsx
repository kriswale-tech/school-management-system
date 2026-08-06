import LevelClassSubjectAccordion from './LevelClassSubjectAccordion'
import type { LevelForSetup } from './types'
import type { CurriculumHandlers } from './handlers'

interface CurriculumLevelsProps {
  levels: LevelForSetup[]
  handlers: CurriculumHandlers
}

const CurriculumLevels = ({ levels, handlers }: CurriculumLevelsProps) => {
  return (
    <div className="space-y-6">
      {levels.map((level) => (
        <LevelClassSubjectAccordion
          key={level.id ?? level.name}
          level={level}
          handlers={handlers}
        />
      ))}
    </div>
  )
}

export default CurriculumLevels
