import LevelClassSubjectAccordion from './LevelClassSubjectAccordion'
import Button from '@/components/ui/Button'
import type { LevelForSetup } from '../../types/types'
import type { ClassSubjectSetupHandlers } from '../../types/class-subject-setup-handlers'

interface ClassSubjectFormProps {
  levels: LevelForSetup[]
  handlers: ClassSubjectSetupHandlers
}

const ClassSubjectForm = ({ levels, handlers }: ClassSubjectFormProps) => {
  return (
    <div className="space-y-6">
      {levels.map((level) => (
        <LevelClassSubjectAccordion
          key={level.id ?? level.name}
          level={level}
          handlers={handlers}
        />
      ))}

      <Button
        type="button"
        variant="outline"
        loading={handlers.isCompleting}
        loadingText="Saving"
        onClick={handlers.onComplete}
      >
        Proceed to next step
      </Button>
    </div>
  )
}

export default ClassSubjectForm
