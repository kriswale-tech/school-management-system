import { Icon } from '@iconify/react'
import Tooltip from '@/components/ui/Tooltip'

const Hint = ({ text }: { text: string }) => (
  <Tooltip content={text} side="bottom" multiline>
    <button type="button" className="text-slate-400 hover:text-slate-700" aria-label="More information">
      <Icon icon="hugeicons:information-circle" className="size-5" />
    </button>
  </Tooltip>
)

export default Hint
