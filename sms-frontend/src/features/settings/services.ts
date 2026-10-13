import api from '@/app/api/api'
import { buildSchoolProfilePayload } from '@/features/setup/school-profile/utils'
import type { SchoolProfile, SchoolProfileFormData } from '@/features/setup/school-profile/types'
import type {
  AcademicYearCalendar,
  AcademicYearSchedulePayload,
  SchoolAlert,
  SchoolSettings,
  TermSwitchPreview,
} from './types'

export const SCHOOL_PROFILE_QUERY_KEY = 'schoolProfile'
export const ACADEMIC_CALENDAR_QUERY_KEY = 'academicYearCalendar'
export const SCHOOL_SETTINGS_QUERY_KEY = 'schoolSettings'
export const SCHOOL_ALERTS_QUERY_KEY = 'schoolAlerts'

export const getSchoolProfile = async () => {
  const response = await api.get<SchoolProfile>('/schools/school/')
  return response.data
}

export const updateSchoolProfile = async (
  data: SchoolProfileFormData,
  logoFile?: File | null,
) => {
  const payload = buildSchoolProfilePayload(data, logoFile)
  payload.append('student_id_prefix', (data.student_id_prefix ?? '').trim())
  const response = await api.patch<SchoolProfile>('/schools/school/', payload)
  return response.data
}

export const getAcademicYearCalendar = async () => {
  const response = await api.get<AcademicYearCalendar>('/schools/settings/academic-years/')
  return response.data
}

export const createNextAcademicYear = async (payload: AcademicYearSchedulePayload) => {
  const response = await api.post<AcademicYearCalendar>('/schools/settings/academic-years/', payload)
  return response.data
}

export const updateAcademicYearDates = async (yearId: string, payload: AcademicYearSchedulePayload) => {
  const response = await api.patch<AcademicYearCalendar>(
    `/schools/settings/academic-years/${yearId}/`,
    payload,
  )
  return response.data
}

export const getTermSwitchPreview = async (termId: string) => {
  const response = await api.get<TermSwitchPreview>(
    `/schools/settings/academic-years/terms/${termId}/switch/`,
  )
  return response.data
}

export const activateTerm = async (termId: string) => {
  const response = await api.post<AcademicYearCalendar>(
    `/schools/settings/academic-years/terms/${termId}/activate/`,
    { acknowledge_warnings: true },
  )
  return response.data
}

export const getSchoolSettings = async () => {
  const response = await api.get<SchoolSettings>('/schools/settings/')
  return response.data
}

export const updateSchoolSettings = async (payload: Partial<SchoolSettings>) => {
  const response = await api.patch<SchoolSettings>('/schools/settings/', payload)
  return response.data
}

export const getSchoolAlerts = async () => {
  const response = await api.get<SchoolAlert[]>('/schools/alerts/')
  return response.data
}
