import SideSlider from '@/components/shared/SideSlider'
import RecordPaymentForm from './RecordPaymentForm'

type RecordPaymentSliderProps = {
  open: boolean
  onClose: () => void
  preselectedStudentId?: string
}

const RecordPaymentSlider = ({
  open,
  onClose,
  preselectedStudentId,
}: RecordPaymentSliderProps) => {
  return (
    <SideSlider open={open} title="Record Fees" onClose={onClose}>
      <RecordPaymentForm
        key={`${open}-${preselectedStudentId ?? 'none'}`}
        preselectedStudentId={preselectedStudentId}
        onSuccess={onClose}
        onCancel={onClose}
      />
    </SideSlider>
  )
}

export default RecordPaymentSlider
