import api from '@/app/api/api'
import type { PaginatedResponse } from '@/types/generalTypes'
import { getQueryUrl } from '@/utils/get-query-url'
import type {
  GuardianCreatePayload,
  GuardianUpdatePayload,
  MarkStudentLeftPayload,
  Parent,
  ParentQueryParams,
  Student,
  StudentBioUpdatePayload,
  StudentDetail,
  StudentFeeHistory,
  StudentFeesQueryParams,
  StudentGuardian,
  StudentOnboardPayload,
  StudentPayment,
  StudentAssessmentsQueryParams,
  StudentPerformance,
  StudentQueryParams,
  StudentStats,
  StudentYearFees,
} from './types'
import type { StudentAssessment, StoredStudentReport } from '@/features/classes/assessment/types'

export const getStudents = async (
  params: StudentQueryParams,
): Promise<PaginatedResponse<Student>> => {
  const url = getQueryUrl<StudentQueryParams>('/students/', params)
  const response = await api.get<PaginatedResponse<Student>>(url)
  return response.data
}

export const getParents = async (
  params: ParentQueryParams = {},
): Promise<PaginatedResponse<Parent>> => {
  const url = getQueryUrl<ParentQueryParams>('/students/parents/', params)
  const response = await api.get<PaginatedResponse<Parent>>(url)
  return response.data
}

export const getStudentStats = async (): Promise<StudentStats> => {
  const response = await api.get<StudentStats>('/students/stats/')
  return response.data
}

export const onboardStudent = async (payload: StudentOnboardPayload): Promise<Student> => {
  const response = await api.post<Student>('/students/onboard/', payload)
  return response.data
}

export const getStudent = async (studentId: string): Promise<StudentDetail> => {
  const response = await api.get<StudentDetail>(`/students/${studentId}/`)
  return response.data
}

export const clearStudentGraduation = async (studentId: string): Promise<StudentDetail> => {
  const response = await api.post<StudentDetail>(`/students/${studentId}/clear-graduation/`)
  return response.data
}

export const markStudentLeft = async (
  studentId: string,
  payload: MarkStudentLeftPayload,
): Promise<StudentDetail> => {
  const response = await api.post<StudentDetail>(`/students/${studentId}/mark-left/`, payload)
  return response.data
}

export const reactivateStudent = async (studentId: string): Promise<StudentDetail> => {
  const response = await api.post<StudentDetail>(`/students/${studentId}/reactivate/`)
  return response.data
}

export const updateStudent = async (
  studentId: string,
  payload: StudentBioUpdatePayload,
): Promise<StudentDetail> => {
  const response = await api.patch<StudentDetail>(`/students/${studentId}/`, payload)
  return response.data
}

export const addStudentGuardian = async (
  studentId: string,
  payload: GuardianCreatePayload,
): Promise<StudentGuardian> => {
  const response = await api.post<StudentGuardian>(`/students/${studentId}/guardians/`, payload)
  return response.data
}

export const updateStudentGuardian = async (
  studentId: string,
  linkId: string,
  payload: GuardianUpdatePayload,
): Promise<StudentGuardian> => {
  const response = await api.patch<StudentGuardian>(
    `/students/${studentId}/guardians/${linkId}/`,
    payload,
  )
  return response.data
}

export const deleteStudentGuardian = async (studentId: string, linkId: string): Promise<void> => {
  await api.delete(`/students/${studentId}/guardians/${linkId}/`)
}

export const getStudentCurrentYearFees = async (
  studentId: string,
  params: StudentFeesQueryParams = {},
): Promise<StudentYearFees> => {
  const url = getQueryUrl(`/students/${studentId}/fees/`, params)
  const response = await api.get<StudentYearFees>(url)
  return response.data
}

export const getStudentFeeHistory = async (
  studentId: string,
  academicYearId?: string,
): Promise<StudentFeeHistory> => {
  const url = getQueryUrl(`/students/${studentId}/fees/history/`, {
    academic_year: academicYearId,
  })
  const response = await api.get<StudentFeeHistory>(url)
  return response.data
}

export const getStudentPayments = async (
  studentId: string,
  params: StudentFeesQueryParams = {},
): Promise<StudentPayment[]> => {
  const url = getQueryUrl(`/students/${studentId}/payments/`, params)
  const response = await api.get<StudentPayment[]>(url)
  return response.data
}

export const getStudentAssessments = async (
  studentId: string,
  params: StudentAssessmentsQueryParams = {},
): Promise<StudentAssessment> => {
  const url = getQueryUrl(`/students/${studentId}/assessments/`, params)
  const response = await api.get<StudentAssessment>(url)
  return response.data
}

export const getStudentPerformance = async (
  studentId: string,
): Promise<StudentPerformance> => {
  const response = await api.get<StudentPerformance>(`/students/${studentId}/performance/`)
  return response.data
}

export const getStudentAssessmentReport = async (
  studentId: string,
  params: StudentAssessmentsQueryParams = {},
): Promise<StoredStudentReport> => {
  const url = getQueryUrl(`/students/${studentId}/assessments/report/`, params)
  const response = await api.get<StoredStudentReport>(url)
  return response.data
}

export const generateStudentAssessmentReport = async (
  studentId: string,
  params: StudentAssessmentsQueryParams = {},
): Promise<StoredStudentReport> => {
  const url = getQueryUrl(`/students/${studentId}/assessments/report/generate/`, params)
  const response = await api.post<StoredStudentReport>(url)
  return response.data
}
