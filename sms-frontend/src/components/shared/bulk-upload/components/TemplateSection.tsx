import { Icon } from '@iconify/react'
import { Button } from '@/components/ui'
import type { TemplateSectionProps } from '../types'

const TemplateSection = ({ hint, onDownloadTemplate }: TemplateSectionProps) => {
  return (
    <div className="flex flex-col gap-4 rounded-lg border border-slate-200 bg-slate-100 p-4 sm:flex-row sm:items-center sm:justify-between">
      <p className="text-sm text-slate-600">{hint}</p>
      <Button
        type="button"
        variant="solidReverse"
        className="w-auto shrink-0 px-4"
        onClick={onDownloadTemplate}
        disabled={!onDownloadTemplate}
      >
        <Icon icon="hugeicons:download-01" className="size-4" />
        Download Template
      </Button>
    </div>
  )
}

export default TemplateSection
