import { useEffect, useRef, useState } from 'react'
import { Icon } from '@iconify/react'
import { Button, FormLabel } from '@/components/ui'
import { mergeClasses } from '@/utils'

const MAX_FILE_SIZE = 2 * 1024 * 1024

export type ImageUploadProps = {
  label: string
  imageUrl?: string
  onImageChange: (_file: File | null) => void
  previewAlt?: string
  helperText?: string
  className?: string
}

const ImageUpload = ({
  label,
  imageUrl,
  onImageChange,
  previewAlt = 'Image preview',
  helperText = 'Recommended size: 256x256px. Max file size: 2MB',
  className,
}: ImageUploadProps) => {
  const inputRef = useRef<HTMLInputElement>(null)
  const [preview, setPreview] = useState<string | null>(null)
  const [removedImageUrl, setRemovedImageUrl] = useState<string | null>(null)
  const [error, setError] = useState('')

  const showPropImage = Boolean(imageUrl && removedImageUrl !== imageUrl)
  const previewSrc = preview ?? (showPropImage ? imageUrl : null)
  const hasImage = Boolean(previewSrc)

  useEffect(() => {
    return () => {
      if (preview) {
        URL.revokeObjectURL(preview)
      }
    }
  }, [preview])

  const handleFileChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    if (!file.type.startsWith('image/')) {
      setError('Please select an image file')
      event.target.value = ''
      return
    }

    if (file.size > MAX_FILE_SIZE) {
      setError('Image must be 2MB or smaller')
      event.target.value = ''
      return
    }

    setError('')

    if (preview) {
      URL.revokeObjectURL(preview)
    }

    setRemovedImageUrl(null)
    setPreview(URL.createObjectURL(file))
    onImageChange(file)
  }

  const handleRemove = () => {
    if (preview) {
      URL.revokeObjectURL(preview)
    }

    setPreview(null)
    setRemovedImageUrl(imageUrl ?? null)
    setError('')

    if (inputRef.current) {
      inputRef.current.value = ''
    }

    onImageChange(null)
  }

  return (
    <div className={className}>
      <FormLabel label={label} className="font-normal text-base" />

      <div className="mt-2 flex items-start gap-4">
        <div
          className={mergeClasses(
            'flex size-20 shrink-0 items-center justify-center overflow-hidden rounded-md border border-slate-200',
            !hasImage && 'bg-slate-50',
          )}
        >
          {previewSrc ? (
            <img src={previewSrc} alt={previewAlt} className="size-full object-cover" />
          ) : (
            <Icon icon="hugeicons:camera-01" className="text-2xl text-slate-400" />
          )}
        </div>

        <div className="space-y-2">
          <div className="flex items-center gap-4">
            <input
              ref={inputRef}
              type="file"
              accept="image/*"
              className="hidden"
              onChange={handleFileChange}
            />
            <Button type="button" className="w-auto px-4" onClick={() => inputRef.current?.click()}>
              Select Photo
            </Button>
            <Button
              type="button"
              variant="outline"
              color="red"
              className="w-auto px-4"
              disabled={!hasImage}
              onClick={handleRemove}
            >
              Remove
            </Button>
          </div>

          {error ? (
            <p className="text-sm text-red-600">{error}</p>
          ) : (
            <p className="text-sm text-slate-500">{helperText}</p>
          )}
        </div>
      </div>
    </div>
  )
}

export default ImageUpload
