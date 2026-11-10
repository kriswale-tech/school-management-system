import axios, { type InternalAxiosRequestConfig } from 'axios'

const baseURL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:9000/api/v1'

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

const api = axios.create({
  baseURL,
  withCredentials: true,
})

api.interceptors.request.use(attachCsrfToken)

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config as InternalAxiosRequestConfig & { _retry?: boolean }
    if (!original || error.response?.status !== 401 || original._retry) {
      return Promise.reject(error)
    }
    if (original.url?.includes('/platform/auth/')) {
      return Promise.reject(error)
    }
    original._retry = true
    try {
      await api.post('/platform/auth/refresh/')
      return api(original)
    } catch {
      return Promise.reject(error)
    }
  },
)

export default api
