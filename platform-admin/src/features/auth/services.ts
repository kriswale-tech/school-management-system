import api from '@/lib/api'
import type { LoginResponse, PlatformSettings, PlatformUser } from './types'

export async function login(email: string, password: string) {
  const { data } = await api.post<LoginResponse>('/platform/auth/login/', {
    email,
    password,
  })
  return data
}

export async function verifyMfa(code: string, mfaToken: string) {
  const { data } = await api.post<LoginResponse>(
    '/platform/auth/mfa/verify/',
    { code, mfa_token: mfaToken },
    {
      headers: { Authorization: `Bearer ${mfaToken}` },
    },
  )
  return data
}

export async function fetchMe() {
  const { data } = await api.get<PlatformUser>('/platform/auth/me/')
  return data
}

export async function logout() {
  await api.post('/platform/auth/logout/')
}

export async function fetchHello() {
  const { data } = await api.get<{
    name: string
    version: string
    authenticated: boolean
    user: PlatformUser | null
  }>('/platform/hello/')
  return data
}

export async function fetchSettings() {
  const { data } = await api.get<PlatformSettings>('/platform/settings/')
  return data
}
