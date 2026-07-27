import { ACCEPTED_MIME_TYPES } from './constants'

export const formatAcceptedExtensions = (extensions: string[]) => {
  return extensions.map((extension) => extension.replace('.', '').toUpperCase()).join(', ')
}

export const getAcceptAttribute = (extensions: string[]) => {
  return [...extensions, ...ACCEPTED_MIME_TYPES].join(',')
}

export const isAcceptedFile = (file: File, extensions: string[]) => {
  const normalizedExtensions = extensions.map((extension) => extension.toLowerCase())
  const fileExtension = `.${file.name.split('.').pop()?.toLowerCase() ?? ''}`

  return (
    normalizedExtensions.includes(fileExtension) ||
    ACCEPTED_MIME_TYPES.includes(file.type)
  )
}

export const isWithinSizeLimit = (file: File, maxFileSizeMb: number) => {
  return file.size <= maxFileSizeMb * 1024 * 1024
}

export const formatFileSize = (bytes: number) => {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}
