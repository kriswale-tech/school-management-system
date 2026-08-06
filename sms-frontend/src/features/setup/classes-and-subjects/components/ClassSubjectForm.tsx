import { CurriculumLevels } from '@/components/curriculum'
import Button from '@/components/ui/Button'
import type { CurriculumHandlers, LevelForSetup } from '@/components/curriculum'

interface ClassSubjectFormProps {
  levels: LevelForSetup[]
  handlers: CurriculumHandlers
  onComplete: () => void
  isCompleting: boolean
}

const ClassSubjectForm = ({
  levels,
  handlers,
  onComplete,
  isCompleting,
}: ClassSubjectFormProps) => {
  return (
    <div className="space-y-6">
      <CurriculumLevels levels={levels} handlers={handlers} />

      <Button
        type="button"
        variant="outline"
        loading={isCompleting}
        loadingText="Saving"
        onClick={onComplete}
      >
        Proceed to next step
      </Button>
    </div>
  )
}

export default ClassSubjectForm
