import type { HTMLAttributes, ReactNode, TdHTMLAttributes, ThHTMLAttributes } from 'react'
import { mergeClasses } from '@/utils'

type TableProps = HTMLAttributes<HTMLTableElement> & {
  children: ReactNode
}

const TableRoot = ({ children, className, ...props }: TableProps) => (
  <table
    className={mergeClasses('min-w-full border-collapse text-left text-sm', className)}
    {...props}
  >
    {children}
  </table>
)

type TableSectionProps = HTMLAttributes<HTMLTableSectionElement> & {
  children: ReactNode
}

const TableHead = ({ children, className, ...props }: TableSectionProps) => (
  <thead className={mergeClasses('bg-slate-200 text-slate-700', className)} {...props}>
    {children}
  </thead>
)

const TableBody = ({ children, className, ...props }: TableSectionProps) => (
  <tbody className={className} {...props}>
    {children}
  </tbody>
)

type TableRowProps = HTMLAttributes<HTMLTableRowElement> & {
  children: ReactNode
}

const TableRow = ({ children, className, ...props }: TableRowProps) => (
  <tr className={mergeClasses('border-b border-slate-200', className)} {...props}>
    {children}
  </tr>
)

type TableHeaderCellProps = ThHTMLAttributes<HTMLTableCellElement> & {
  children: ReactNode
}

const TableHeaderCell = ({ children, className, ...props }: TableHeaderCellProps) => (
  <th className={mergeClasses('px-4 py-3 font-medium', className)} {...props}>
    {children}
  </th>
)

type TableCellVariant = 'default' | 'primary'

type TableCellProps = TdHTMLAttributes<HTMLTableCellElement> & {
  children: ReactNode
  variant?: TableCellVariant
}

const tableCellVariantClasses: Record<TableCellVariant, string> = {
  default: 'text-slate-700',
  primary: 'font-medium text-slate-900',
}

const TableCell = ({ children, className, variant = 'default', ...props }: TableCellProps) => (
  <td
    className={mergeClasses('px-4 py-3', tableCellVariantClasses[variant], className)}
    {...props}
  >
    {children}
  </td>
)

type TableScrollProps = HTMLAttributes<HTMLDivElement> & {
  children: ReactNode
}

const TableScroll = ({ children, className, ...props }: TableScrollProps) => (
  <div className={mergeClasses('overflow-x-auto', className)} {...props}>
    {children}
  </div>
)

const Table = Object.assign(TableRoot, {
  Head: TableHead,
  Body: TableBody,
  Row: TableRow,
  HeaderCell: TableHeaderCell,
  Cell: TableCell,
  Scroll: TableScroll,
})

export default Table
