import api from '@/app/api/api'
import { getQueryUrl } from '@/utils/get-query-url'
import type {
  AllClassesQueryParams,
  AllClassesResponse,
  AssignClassTeacherPayload,
  AssignSubjectTeacherPayload,
  ClassDetail,
  ClassListQueryParams,
  ClassListResponse,
  ClassStats,
  ClassStudentListResponse,
  ClassSubjectListResponse,
  ClassTeacherOptionListResponse,
} from './types'

export const getClasses = async () => {
  const response = await api.get<{ name: string; id: string }[]>('/academics/class-levels/')
  return response.data
}

export const getLevels = async () => {
  const response = await api.get<{ name: string; id: string }[]>('/academics/levels/')
  return response.data
}

export const getAllClasses = async (
  params: AllClassesQueryParams = {},
): Promise<AllClassesResponse> => {
  const url = getQueryUrl<AllClassesQueryParams>('/academics/levels/all-classes/', params)
  const response = await api.get<AllClassesResponse>(url)
  return response.data
}

export const getClassList = async (
  params: ClassListQueryParams = {},
): Promise<ClassListResponse> => {
  const url = getQueryUrl<ClassListQueryParams>('/academics/classes/', params)
  const response = await api.get<ClassListResponse>(url)
  return response.data
}

export const getClassStats = async (): Promise<ClassStats> => {
  const response = await api.get<ClassStats>('/academics/classes/stats/')
  return response.data
}

export const getClassDetail = async (streamId: string): Promise<ClassDetail> => {
  const response = await api.get<ClassDetail>(`/academics/classes/${streamId}/`)
  return response.data
}

export const getClassStudents = async (
  streamId: string,
  params: { search?: string } = {},
): Promise<ClassStudentListResponse> => {
  const url = getQueryUrl(`/academics/classes/${streamId}/students/`, params)
  const response = await api.get<ClassStudentListResponse>(url)
  return response.data
}

export const getClassSubjects = async (streamId: string): Promise<ClassSubjectListResponse> => {
  const response = await api.get<ClassSubjectListResponse>(
    `/academics/classes/${streamId}/subjects/`,
  )
  return response.data
}

export const getClassTeacherOptions = async (
  params: { search?: string } = {},
): Promise<ClassTeacherOptionListResponse> => {
  const url = getQueryUrl('/academics/classes/teachers/', params)
  const response = await api.get<ClassTeacherOptionListResponse>(url)
  return response.data
}

export const assignClassTeacher = async (
  streamId: string,
  payload: AssignClassTeacherPayload,
): Promise<ClassDetail> => {
  const response = await api.put<ClassDetail>(
    `/academics/classes/${streamId}/class-teacher/`,
    payload,
  )
  return response.data
}

export const assignSubjectTeacher = async (
  streamId: string,
  payload: AssignSubjectTeacherPayload,
): Promise<ClassSubjectListResponse> => {
  const response = await api.put<ClassSubjectListResponse>(
    `/academics/classes/${streamId}/subject-teacher/`,
    payload,
  )
  return response.data
}
