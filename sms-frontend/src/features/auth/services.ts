import api from '@/app/api/api'
import type { InternalAxiosRequestConfig } from 'axios'
import type {
  AuthResponse,
  SelectSchoolData,
  SignupData,
  User,
  VerifyOTPData,
} from './types'

export type PublicConfig = {
  public_school_registration_enabled: boolean
}

export type SchoolAdminInvitePreview = {
  school_name: string
  phone_number: string
  email: string
  first_name: string
  last_name: string
  status: string
  expires_at: string
  school_status: string
}

export type SchoolAdminInviteAcceptResult = {
  message: string
  school_id: string
  school_name: string
  phone_number: string
  created_user: boolean
}

export const getPublicConfig = async () => {
  const response = await api.get<PublicConfig>('/platform/public-config/')
  return response.data
}

// signup endpoing
export const signup = async (data: SignupData) => {
  const response = await api.post<{ message: string }>('/accounts/signup/', data)
  return response.data
}

export const getSchoolAdminInvite = async (token: string) => {
  const response = await api.get<SchoolAdminInvitePreview>(`/accounts/invites/${token}/`)
  return response.data
}

export const acceptSchoolAdminInvite = async (token: string) => {
  const response = await api.post<SchoolAdminInviteAcceptResult>(
    `/accounts/invites/${token}/accept/`,
  )
  return response.data
}

// verify OTP endpoint
export const verifyOTP = async (data: VerifyOTPData) => {
  const response = await api.post<AuthResponse>('/accounts/verify-otp/', data)
  return response.data
}

// resend OTP endpoint
export const resendOTP = async (data: {phone_number: string}) => {
  const response = await api.post<{ message: string }>('/accounts/resend-otp/', data)
  return response.data
}

// get user endpoint
export const getUser = async () => {
  const response = await api.get<User>('/accounts/me/')
  return response.data
}

// logout endpoint
export const logout = async () => {
  const response = await api.post<{ message: string }>(
    '/accounts/logout/',
    {},
    { _skipAuthRefresh: true } as InternalAxiosRequestConfig,
  )
  return response.data
}

// refresh token endpoint
export const refreshToken = async () => {
  const response = await api.post<{ message: string }>('/accounts/refresh/')
  return response.data
}

// login endpoint
export const login = async (data: {phone_number: string}) => {
  const response = await api.post<{ message: string }>('/accounts/login/', data)
  return response.data
}

// verify login OTP endpoint
export const verifyLoginOTP = async (data: VerifyOTPData) => {
  const response = await api.post<AuthResponse>('/accounts/login/verify-otp/', data)
  return response.data
}

// resend login OTP endpoint
export const resendLoginOTP = async (data: {phone_number: string}) => {
  const response = await api.post<{ message: string }>('/accounts/login/resend-otp/', data)
  return response.data
}

// select or switch school (scopes session and re-issues auth cookies)
export const selectSchool = async (data: SelectSchoolData) => {
  const response = await api.post<AuthResponse>('/accounts/select-school/', data)
  return response.data
}
