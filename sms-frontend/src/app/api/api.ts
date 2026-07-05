import axios, { type InternalAxiosRequestConfig } from 'axios'
import { useAuthStore } from '@/features/auth/store'

declare module 'axios' {
  export interface InternalAxiosRequestConfig {
    _retry?: boolean
    _skipAuthRefresh?: boolean
  }
}

const baseURL = 'http://localhost:9000/api/v1'

function getCsrfToken(): string | null {
  const match = document.cookie.match(/csrftoken=([^;]+)/)
  return match ? decodeURIComponent(match[1]) : null
}

function attachCsrfToken(config: InternalAxiosRequestConfig) {
  const method = config.method?.toLowerCase()
  if (method && ['post', 'put', 'patch', 'delete'].includes(method)) {
    const csrfToken = getCsrfToken()
    if (csrfToken) {
      config.headers['X-CSRFToken'] = csrfToken
    }
  }
  return config
}

const refreshClient = axios.create({
  baseURL,
  withCredentials: true,
})

refreshClient.interceptors.request.use(attachCsrfToken)

const api = axios.create({
  baseURL,
  withCredentials: true,
})

api.interceptors.request.use(attachCsrfToken)

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config

    if (!original || error.response?.status !== 401 || original._skipAuthRefresh) {
      return Promise.reject(error)
    }

    if (original._retry) {
      await useAuthStore.getState().logout()
      return Promise.reject(error)
    }

    original._retry = true

    try {
      await refreshClient.post('/accounts/refresh/')
      return api(original)
    } catch {
      await useAuthStore.getState().logout()
    }

    return Promise.reject(error)
  },
)

export default api
