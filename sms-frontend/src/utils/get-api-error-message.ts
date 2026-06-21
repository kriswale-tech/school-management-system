import { isAxiosError } from 'axios'

export function getApiErrorMessage(error: unknown, fallback: string): string {
  if (!isAxiosError(error)) return fallback

  const data = error.response?.data
  if (typeof data !== 'object' || data === null) return fallback

  if ('message' in data && typeof data.message === 'string') {
    return data.message
  }

  if ('detail' in data && typeof data.detail === 'string') {
    return data.detail
  }

  for (const value of Object.values(data)) {
    if (Array.isArray(value) && typeof value[0] === 'string') {
      return value[0]
    }
  }

  return fallback
}
