import toast from 'react-hot-toast'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Icon } from '@iconify/react'
import { ConfirmDialog } from '@/components/shared'
import { getApiErrorMessage } from '@/utils'
import { deleteFeeItem } from '../services'
import type { FeeItem } from '../types'
import { buildAppliesToDisplay, formatFeeAmount } from '../utils'
import EditFeeItem from './EditFeeItem'

type FeesSetupTableProps = {
  feeItems: FeeItem[]
}

const FeesSetupTable = ({ feeItems }: FeesSetupTableProps) => {
  const queryClient = useQueryClient()
  const [editingItem, setEditingItem] = useState<FeeItem | null>(null)
  const [deletingItem, setDeletingItem] = useState<FeeItem | null>(null)

  const { mutate: removeFeeItem, isPending: isDeleting } = useMutation({
    mutationFn: deleteFeeItem,
    onSuccess: () => {
      toast.success('Fee item deleted')
      void queryClient.invalidateQueries({ queryKey: ['feeStructures'] })
      setDeletingItem(null)
    },
    onError: (error) => {
      toast.error(getApiErrorMessage(error, 'Unable to delete fee item'))
    },
  })

  return (
    <>
      <div className="form-field-wrapper py-10 bg-slate-50 overflow-x-auto">
        <table className="min-w-full border-collapse text-left text-sm">
          <thead className="bg-slate-200 text-slate-700">
            <tr>
              <th className="px-4 py-3 font-medium">Fee Item</th>
              <th className="px-4 py-3 font-medium">Amount</th>
              <th className="px-4 py-3 font-medium">Applies to</th>
              <th className="px-4 py-3 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {feeItems.length === 0 ? (
              <tr className="border-b border-slate-200">
                <td colSpan={4} className="px-4 py-6 text-center text-slate-500">
                  No fee items added yet.
                </td>
              </tr>
            ) : (
              feeItems.map((fee) => (
                <tr key={fee.id} className="border-b border-slate-200">
                  <td className="px-4 py-3 font-medium text-slate-900">{fee.name}</td>
                  <td className="px-4 py-3 text-slate-700">{formatFeeAmount(fee.amount)}</td>
                  <td className="px-4 py-3 text-slate-700">{buildAppliesToDisplay(fee)}</td>
                  <td className="px-4 py-3">
                    <div className="flex shrink-0 items-center gap-1">
                      <button
                        type="button"
                        title={`Edit ${fee.name}`}
                        aria-label={`Edit ${fee.name}`}
                        onClick={() => setEditingItem(fee)}
                        className="flex size-8 shadow-sm bg-white items-center justify-center rounded-full border border-slate-200 text-slate-600 hover:bg-slate-50 hover:text-slate-900"
                      >
                        <Icon icon="hugeicons:edit-02" className="size-4" />
                      </button>
                      <button
                        type="button"
                        title={`Delete ${fee.name}`}
                        aria-label={`Delete ${fee.name}`}
                        onClick={() => setDeletingItem(fee)}
                        className="flex size-8 shadow-sm bg-white items-center justify-center rounded-full border border-slate-200 text-red-600 hover:bg-red-50 hover:text-red-700"
                      >
                        <Icon icon="hugeicons:delete-02" className="size-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <EditFeeItem
        open={Boolean(editingItem)}
        feeItem={editingItem}
        onClose={() => setEditingItem(null)}
      />

      <ConfirmDialog
        open={Boolean(deletingItem)}
        title="Delete fee item"
        message={`Are you sure you want to delete "${deletingItem?.name}"? This action cannot be undone.`}
        confirmLabel="Delete"
        onClose={() => setDeletingItem(null)}
        onConfirm={() => {
          if (deletingItem) removeFeeItem(deletingItem.id)
        }}
        isLoading={isDeleting}
      />
    </>
  )
}

export default FeesSetupTable
