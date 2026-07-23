import toast from 'react-hot-toast'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { Icon } from '@iconify/react'
import { ConfirmDialog, Table, TableWrapper } from '@/components/shared'
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
      <TableWrapper
        isEmpty={feeItems.length === 0}
        emptyState={{
          title: 'No fee items added yet',
          description: 'Use the form above to add your first fee item.',
        }}
        skeletonColumns={4}
        variant="form-field"
      >
        <Table>
          <Table.Head>
            <Table.Row className="border-b-0">
              <Table.HeaderCell>Fee Item</Table.HeaderCell>
              <Table.HeaderCell>Amount</Table.HeaderCell>
              <Table.HeaderCell>Applies to</Table.HeaderCell>
              <Table.HeaderCell>Actions</Table.HeaderCell>
            </Table.Row>
          </Table.Head>
          <Table.Body>
            {feeItems.map((fee) => (
              <Table.Row key={fee.id}>
                <Table.Cell variant="primary">{fee.name}</Table.Cell>
                <Table.Cell>{formatFeeAmount(fee.amount)}</Table.Cell>
                <Table.Cell>{buildAppliesToDisplay(fee)}</Table.Cell>
                <Table.Cell>
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
                </Table.Cell>
              </Table.Row>
            ))}
          </Table.Body>
        </Table>
      </TableWrapper>

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
