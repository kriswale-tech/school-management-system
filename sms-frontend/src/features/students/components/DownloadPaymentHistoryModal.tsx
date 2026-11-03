import { useState } from 'react'
import { useMutation } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { Button, FormLabel, Modal, SelectField } from '@/components/ui'
import { getApiErrorMessage } from '@/utils'
import { downloadStudentPaymentHistory } from '../services'
import type { PaymentHistoryExportScope } from '../types'

type DownloadPaymentHistoryModalProps = {
  open: boolean
  onClose: () => void
  studentId: string
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
  studentId,
  academicYearOptions,
  termOptions,
}: DownloadPaymentHistoryModalProps) => {
  const [scope, setScope] = useState<PaymentHistoryExportScope>('all_time')
  const [academicYearId, setAcademicYearId] = useState('')
  const [termId, setTermId] = useState('')

  const handleClose = () => {
    setScope('all_time')
    setAcademicYearId('')
    setTermId('')
    onClose()
  }

  const { mutate: download, isPending } = useMutation({
    mutationFn: () =>
      downloadStudentPaymentHistory(studentId, {
        scope,
        academic_year: scope === 'academic_year' ? academicYearId : undefined,
        term: scope === 'term' ? termId : undefined,
      }),
    onSuccess: () => {
      toast.success('Payment history downloaded')
      handleClose()
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, 'Unable to download payment history'))
    },
  })

  const canDownload =
    Boolean(studentId) &&
    (scope === 'all_time' ||
      (scope === 'academic_year' && Boolean(academicYearId)) ||
      (scope === 'term' && Boolean(termId)))

  return (
    <Modal open={open} title="Download payment history" onClose={handleClose}>
      <div className="space-y-4">
        <div className="space-y-2">
          <FormLabel label="Range" />
          <SelectField
            options={SCOPE_OPTIONS}
            value={scope}
            onChange={(value) => setScope(value as PaymentHistoryExportScope)}
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

        <div className="flex justify-end gap-2 pt-2">
          <Button type="button" variant="ghost" className="w-fit" onClick={handleClose}>
            Cancel
          </Button>
          <Button
            type="button"
            className="w-fit"
            loading={isPending}
            loadingText="Downloading..."
            disabled={!canDownload || isPending}
            onClick={() => download()}
          >
            Download Excel
          </Button>
        </div>
      </div>
    </Modal>
  )
}

export default DownloadPaymentHistoryModal
