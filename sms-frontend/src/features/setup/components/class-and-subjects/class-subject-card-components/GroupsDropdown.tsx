import { Icon } from '@iconify/react'
import Button from '@/components/ui/Button'
import type { SubjectGroupForSetup } from '../../../types/types'
import IconActionButton from './IconActionButton'
import { useAnchoredDropdown } from './dropdown-utils'

const GroupsDropdown = ({
  groups,
  onEdit,
  onDelete,
  onAddGroup,
}: {
  groups: SubjectGroupForSetup[]
  onEdit: (groupId: string, initialName: string) => void
  onDelete: (groupId: string, name: string) => void
  onAddGroup?: () => void
}) => {
  const { isOpen, panelStyle, containerRef, toggleOpen, close } = useAnchoredDropdown()

  return (
    <div ref={containerRef} className="relative">
      <Button
        type="button"
        variant="ghost"
        title="Subject groups"
        className="w-fit rounded-full p-0.5 px-1.5 gap-0.5 text-xs"
        onClick={toggleOpen}
      >
        <Icon icon="ph:stack" className="size-4" />
        <span>{groups.length}</span>
      </Button>

      {isOpen && (
        <div className="bg-white p-2 shadow-lg" style={panelStyle}>
          <ul className="max-h-52 space-y-1 overflow-y-auto">
            {groups.length === 0 ? (
              <li className="px-2 py-1.5 text-sm text-slate-400">No groups</li>
            ) : (
              groups.map((group) => (
                <li
                  key={group.id ?? group.name}
                  className="flex items-center justify-between gap-2 px-2 py-1.5 text-sm text-slate-600 hover:bg-slate-50"
                >
                  <span className="min-w-0 flex-1 truncate" title={group.name}>
                    {group.name}
                  </span>
                  <div className="flex shrink-0 items-center gap-0.5">
                    {group.id && (
                      <>
                        <IconActionButton
                          icon="hugeicons:edit-02"
                          label="Edit group"
                          onClick={() => {
                            onEdit(group.id!, group.name)
                            close()
                          }}
                        />
                        <IconActionButton
                          variant="danger"
                          icon="ic:outline-remove-circle-outline"
                          label="Remove group"
                          onClick={() => {
                            onDelete(group.id!, group.name)
                            close()
                          }}
                        />
                      </>
                    )}
                  </div>
                </li>
              ))
            )}
          </ul>

          {onAddGroup && (
            <button
              type="button"
              onClick={() => {
                close()
                onAddGroup()
              }}
              className="mt-2 flex w-full items-center justify-center gap-1 border border-slate-300 px-2 py-1.5 text-xs text-slate-700 hover:bg-slate-50"
            >
              <Icon icon="hugeicons:plus-sign" className="size-3.5" />
              <span>Add group</span>
            </button>
          )}
        </div>
      )}
    </div>
  )
}

export default GroupsDropdown
