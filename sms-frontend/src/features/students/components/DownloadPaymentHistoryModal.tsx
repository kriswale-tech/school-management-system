import { useState } from 'react'
import { Button, FormLabel, Modal, SelectField } from '@/components/ui'

export type PaymentDownloadScope = 'all_time' | 'academic_year' | 'term'

type DownloadPaymentHistoryModalProps = {
  open: boolean
  onClose: () => void
  academicYearOptions: { value: string; label: string }[]
  termOptions: { value: string; label: string }[]
}

const SCOPE_OPTIONS = [
  { value: 'all_time', label: 'All time' },
  { value: 'academic_year', label: 'Academic year' },
  { value: 'term', label: 'Term' },
]

const DownloadPaymentHistoryModal = ({
  open,
  onClose,
  academicYearOptions,
  termOptions,
}: DownloadPaymentHistoryModalProps) => {
  const [scope, setScope] = useState<PaymentDownloadScope>('all_time')
  const [academicYearId, setAcademicYearId] = useState('')
  const [termId, setTermId] = useState('')

  const handleClose = () => {
    setScope('all_time')
    setAcademicYearId('')
    setTermId('')
    onClose()
  }

  return (
    <Modal open={open} title="Download payment history" onClose={handleClose}>
      <div className="space-y-4">
        <div className="space-y-2">
          <FormLabel label="Range" />
          <SelectField
            options={SCOPE_OPTIONS}
            value={scope}
            onChange={(value) => setScope(value as PaymentDownloadScope)}
            placeholder="Select range"
          />
        </div>

        {scope === 'academic_year' ? (
          <div className="space-y-2">
            <FormLabel label="Academic year" />
            <SelectField
              options={academicYearOptions}
              value={academicYearId}
              onChange={setAcademicYearId}
              placeholder="Select academic year"
            />
          </div>
        ) : null}

        {scope === 'term' ? (
          <div className="space-y-2">
            <FormLabel label="Term" />
            <SelectField
              options={termOptions}
              value={termId}
              onChange={setTermId}
              placeholder="Select term"
            />
          </div>
        ) : null}

        <p className="text-sm text-slate-500">
          Excel export will be available in a later release. Your filter choice will be used then.
        </p>

        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="ghost" className="w-fit" onClick={handleClose}>
            Cancel
          </Button>
          <Button type="button" className="w-fit" disabled>
            Download Excel
          </Button>
        </div>
      </div>
    </Modal>
  )
}

export default DownloadPaymentHistoryModal
