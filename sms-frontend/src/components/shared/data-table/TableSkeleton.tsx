import Table from './Table'

export type TableSkeletonProps = {
  columns: number
  rows?: number
}

const TableSkeleton = ({ columns, rows = 5 }: TableSkeletonProps) => {
  return (
    <Table>
      <Table.Head>
        <Table.Row className="border-b-0">
          {Array.from({ length: columns }).map((_, index) => (
            <Table.HeaderCell key={`head-${index}`}>
              <div className="h-4 w-24 animate-pulse rounded bg-slate-300" />
            </Table.HeaderCell>
          ))}
        </Table.Row>
      </Table.Head>
      <Table.Body>
        {Array.from({ length: rows }).map((_, rowIndex) => (
          <Table.Row key={`row-${rowIndex}`}>
            {Array.from({ length: columns }).map((__, cellIndex) => (
              <Table.Cell key={`cell-${rowIndex}-${cellIndex}`}>
                <div
                  className="h-4 animate-pulse rounded bg-slate-200"
                  style={{ width: `${60 + ((cellIndex * 17) % 40)}%` }}
                />
              </Table.Cell>
            ))}
          </Table.Row>
        ))}
      </Table.Body>
    </Table>
  )
}

export default TableSkeleton
