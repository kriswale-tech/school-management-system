import type { ReactNode } from 'react'
import EmptyState, { type EmptyStateProps } from '../EmptyState'
import type { PaginatedResponse } from '@/types/generalTypes'
import { mergeClasses } from '@/utils'
import Pagination from './Pagination'
import TableSkeleton from './TableSkeleton'

export type TableWrapperVariant = 'form-field' | 'card'

export type TableWrapperProps = {
  children: ReactNode
  variant?: TableWrapperVariant
  isLoading?: boolean
  isEmpty?: boolean
  emptyState?: EmptyStateProps
  pagination?: PaginatedResponse<unknown> | null
  onPageChange?: (page: number) => void
  skeletonColumns?: number
  skeletonRows?: number
  className?: string
}

const variantClasses: Record<TableWrapperVariant, string> = {
  'form-field': 'form-field-wrapper overflow-x-auto py-5 bg-slate-50',
  card: 'form-field-wrapper overflow-x-auto py-5 bg-white rounded-none border-none custom-shadow-md',
}

const TableWrapper = ({
  children,
  variant = 'card',
  isLoading = false,
  isEmpty = false,
  emptyState,
  pagination = null,
  onPageChange,
  skeletonColumns = 4,
  skeletonRows = 5,
  className,
}: TableWrapperProps) => {
  const showPagination = Boolean(pagination && onPageChange && !isLoading && !isEmpty)

  return (
    <div className={mergeClasses(variantClasses[variant], className)}>
      {isLoading ? (
        <TableSkeleton columns={skeletonColumns} rows={skeletonRows} />
      ) : isEmpty && emptyState ? (
        <EmptyState
          {...emptyState}
          unstyled
          className={mergeClasses('py-12', emptyState.className)}
        />
      ) : isEmpty ? (
        <EmptyState title="No results found" unstyled className="py-12" />
      ) : (
        children
      )}

      {showPagination && pagination && onPageChange ? (
        <Pagination pagination={pagination} onPageChange={onPageChange} isLoading={isLoading} />
      ) : null}
    </div>
  )
}

export default TableWrapper
