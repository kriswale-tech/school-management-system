import { Icon } from '@iconify/react'
import Button from '@/components/ui/Button'
import type { StreamForSetup } from '../../types'
import type { AddStreamPayload } from '../../class-subject-setup-types'
import IconActionButton from './IconActionButton'
import { useAnchoredDropdown } from './dropdown-utils'

const StreamsDropdown = ({
  streams,
  onEdit,
  onDelete,
  onAddStream,
}: {
  streams: StreamForSetup[]
  onEdit: (streamId: string, initialValues: AddStreamPayload) => void
  onDelete: (streamId: string, name: string) => void
  onAddStream?: () => void
}) => {
  const { isOpen, panelStyle, containerRef, toggleOpen, close } = useAnchoredDropdown()

  return (
    <div ref={containerRef} className="relative">
      <Button
        type="button"
        variant="ghost"
        title="Class streams"
        className="w-fit rounded-full p-0.5 px-1.5 gap-0.5 text-xs"
        onClick={toggleOpen}
      >
        <Icon icon="ph:tree-structure-light" className="size-4" />
        <span>{streams.length}</span>
      </Button>

      {isOpen && (
        <div className="bg-white p-2 shadow-lg" style={panelStyle}>
          <ul className="max-h-52 space-y-1 overflow-y-auto">
            {streams.length === 0 ? (
              <li className="px-2 py-1.5 text-sm text-slate-400">No streams</li>
            ) : (
              streams.map((stream) => {
                const streamName = stream.name || stream.full_name
                return (
                  <li
                    key={stream.id}
                    className="flex items-center justify-between gap-2 px-2 py-1.5 text-sm text-slate-600 hover:bg-slate-50"
                  >
                    <span className="min-w-0 flex-1 truncate" title={streamName}>
                      {streamName}
                    </span>
                    <div className="flex shrink-0 items-center gap-0.5">
                      <IconActionButton
                        icon="hugeicons:edit-02"
                        label="Edit stream"
                        onClick={() => {
                          onEdit(stream.id, {
                            name: stream.name,
                            description: stream.description ?? undefined,
                          })
                          close()
                        }}
                      />
                      <IconActionButton
                        variant="danger"
                        icon="ic:outline-remove-circle-outline"
                        label="Remove stream"
                        onClick={() => {
                          onDelete(stream.id, streamName)
                          close()
                        }}
                      />
                    </div>
                  </li>
                )
              })
            )}
          </ul>

          {onAddStream && (
            <button
              type="button"
              onClick={() => {
                close()
                onAddStream()
              }}
              className="mt-2 flex w-full items-center justify-center gap-1 border border-slate-300 px-2 py-1.5 text-xs text-slate-700 hover:bg-slate-50"
            >
              <Icon icon="hugeicons:plus-sign" className="size-3.5" />
              <span>Add stream</span>
            </button>
          )}
        </div>
      )}
    </div>
  )
}

export default StreamsDropdown
