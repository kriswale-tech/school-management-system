import { useQuery } from '@tanstack/react-query'
import { Button, Modal } from '@/components/ui'
import LoadingSpinner from '@/components/ui/LoadingSpinner'
import { getApiErrorMessage } from '@/utils'
import { getTermSwitchPreview } from '../services'

type SwitchTermDialogProps = {
  termId: string | null
  isSwitching: boolean
  onClose: () => void
  onConfirm: () => void
}

const SwitchTermDialog = ({ termId, isSwitching, onClose, onConfirm }: SwitchTermDialogProps) => {
  const { data, isLoading, isError, error } = useQuery({
    queryKey: ['termSwitchPreview', termId],
    queryFn: () => getTermSwitchPreview(termId as string),
    enabled: Boolean(termId),
  })

  return (
    <Modal open={Boolean(termId)} title="Make this the current term" onClose={onClose}>
      <div className="space-y-4">
        {isLoading ? <LoadingSpinner className="mx-auto" /> : null}
        {isError ? (
          <p className="text-sm text-red-600">
            {getApiErrorMessage(error, 'Unable to check this term.')}
          </p>
        ) : null}
        {data ? (
          <>
            <p className="text-sm text-slate-600">
              Students, fees, and assessments will open on {data.term_label}. Past marks, bills,
              and class lists stay on the term you are leaving.
            </p>
            {data.blockers.length > 0 ? (
              <ul className="list-disc space-y-1 pl-5 text-sm text-red-700">
                {data.blockers.map((blocker) => (
                  <li key={blocker}>{blocker}</li>
                ))}
              </ul>
            ) : null}
            {data.warnings.length > 0 ? (
              <ul className="list-disc space-y-1 pl-5 text-sm text-amber-800">
                {data.warnings.map((warning) => (
                  <li key={warning}>{warning}</li>
                ))}
              </ul>
            ) : null}
          </>
        ) : null}
        <div className="grid grid-cols-2 gap-3">
          <Button type="button" variant="outline" onClick={onClose} disabled={isSwitching}>
            Cancel
          </Button>
          <Button
            type="button"
            onClick={onConfirm}
            loading={isSwitching}
            disabled={!data?.can_switch || isLoading}
          >
            Switch term
          </Button>
        </div>
      </div>
    </Modal>
  )
}

export default SwitchTermDialog
