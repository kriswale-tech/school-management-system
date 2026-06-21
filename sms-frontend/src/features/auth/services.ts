import api from '@/app/api/api'
import type { InternalAxiosRequestConfig } from 'axios'
import type { SignupData, VerifyOTPData, User } from './types'

// signup endpoing
export const signup = async (data: SignupData) => {
  const response = await api.post<{ message: string }>('/accounts/signup/', data)
  return response.data
}

// verify OTP endpoint
export const verifyOTP = async (data: VerifyOTPData) => {
  const response = await api.post<{ message: string }>('/accounts/verify-otp/', data)
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
  const response = await api.post<{ message: string }>('/accounts/login/verify-otp/', data)
  return response.data
}

// resend login OTP endpoint
export const resendLoginOTP = async (data: {phone_number: string}) => {
  const response = await api.post<{ message: string }>('/accounts/login/resend-otp/', data)
  return response.data
}