import { useRef, useState } from 'react'
import { Icon } from '@iconify/react'
import { Button } from '@/components/ui'
import { mergeClasses } from '@/utils'
import { formatAcceptedExtensions, getAcceptAttribute, isAcceptedFile, isWithinSizeLimit } from '../utils'
import type { DropZoneProps } from '../types'

const DropZone = ({
  acceptedExtensions,
  maxFileSizeMb,
  error,
  onFileSelect,
  onError,
}: DropZoneProps) => {
  const inputRef = useRef<HTMLInputElement>(null)
  const [isDragging, setIsDragging] = useState(false)

  const acceptedTypesLabel = formatAcceptedExtensions(acceptedExtensions)

  const handleFile = (file: File | undefined) => {
    if (!file) return

    if (!isAcceptedFile(file, acceptedExtensions)) {
      onError(`Please upload a ${acceptedTypesLabel} file`)
      return
    }

    if (!isWithinSizeLimit(file, maxFileSizeMb)) {
      onError(`File must be ${maxFileSizeMb}MB or smaller`)
      return
    }

    onError('')
    onFileSelect(file)
  }

  const handleInputChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    handleFile(event.target.files?.[0])
    event.target.value = ''
  }

  const handleDrop = (event: React.DragEvent<HTMLDivElement>) => {
    event.preventDefault()
    setIsDragging(false)
    handleFile(event.dataTransfer.files?.[0])
  }

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={() => inputRef.current?.click()}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault()
          inputRef.current?.click()
        }
      }}
      onDragOver={(event) => {
        event.preventDefault()
        setIsDragging(true)
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
      className={mergeClasses(
        'flex cursor-pointer flex-col items-center rounded-lg border border-dashed border-slate-300 bg-slate-100 px-6 py-10 text-center transition-colors',
        isDragging && 'border-slate-400 bg-slate-200/70',
      )}
    >
      <input
        ref={inputRef}
        type="file"
        accept={getAcceptAttribute(acceptedExtensions)}
        className="hidden"
        onChange={handleInputChange}
      />

      <div className="mb-4 flex size-12 items-center justify-center rounded-full bg-white shadow-sm">
        <Icon icon="hugeicons:upload-01" className="size-5 text-slate-700" />
      </div>

      <p className="text-sm font-medium text-slate-900">Click to upload or drag and drop</p>
      <p className="mt-1 text-sm text-slate-500">
        {acceptedTypesLabel} and similar files up to {maxFileSizeMb}MB
      </p>

      {error ? <p className="mt-2 text-sm text-red-600">{error}</p> : null}

      <Button
        type="button"
        variant="solid"
        className="mt-5 w-auto px-4"
        onClick={(event) => {
          event.stopPropagation()
          inputRef.current?.click()
        }}
      >
        Browse files
      </Button>
    </div>
  )
}

export default DropZone
