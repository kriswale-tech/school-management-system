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
  SubjectGroupCandidateList,
  TeachingAssignmentDetail,
} from './types'
import type {
  AdminAssessmentDetail,
  AdminAssessmentFilterOptions,
  AdminAssessmentOverview,
  AssessmentWorkspace,
  CaItem,
  CaItemWritePayload,
  ClassTeacherAssessmentDetail,
  ClassTeacherAssessmentOverview,
  SaveMarksPayload,
} from './assessment/types'

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

export const getTeachingAssignmentDetail = async (
  assignmentId: string,
): Promise<TeachingAssignmentDetail> => {
  const response = await api.get<TeachingAssignmentDetail>(
    `/academics/teaching-assignments/${assignmentId}/`,
  )
  return response.data
}

export const getTeachingAssignmentStudents = async (
  assignmentId: string,
  params: { search?: string } = {},
): Promise<ClassStudentListResponse> => {
  const url = getQueryUrl(`/academics/teaching-assignments/${assignmentId}/students/`, params)
  const response = await api.get<ClassStudentListResponse>(url)
  return response.data
}

export const getSubjectGroupCandidates = async (
  assignmentId: string,
  params: { search?: string } = {},
): Promise<SubjectGroupCandidateList> => {
  const url = getQueryUrl(
    `/academics/teaching-assignments/${assignmentId}/group-candidates/`,
    params,
  )
  const response = await api.get<SubjectGroupCandidateList>(url)
  return response.data
}

export const assignSubjectGroupStudents = async (
  assignmentId: string,
  studentIds: string[],
): Promise<TeachingAssignmentDetail> => {
  const response = await api.post<TeachingAssignmentDetail>(
    `/academics/teaching-assignments/${assignmentId}/assign-students/`,
    { student_ids: studentIds },
  )
  return response.data
}

export const unassignSubjectGroupStudents = async (
  assignmentId: string,
  studentIds: string[],
): Promise<TeachingAssignmentDetail> => {
  const response = await api.post<TeachingAssignmentDetail>(
    `/academics/teaching-assignments/${assignmentId}/unassign-students/`,
    { student_ids: studentIds },
  )
  return response.data
}

export const getTeachingAssignmentWorkspace = async (
  assignmentId: string,
): Promise<AssessmentWorkspace> => {
  const response = await api.get<AssessmentWorkspace>(
    `/academics/teaching-assignments/${assignmentId}/workspace/`,
  )
  return response.data
}

export const createTeachingAssignmentCaItem = async (
  assignmentId: string,
  payload: CaItemWritePayload,
): Promise<CaItem> => {
  const response = await api.post<CaItem>(
    `/academics/teaching-assignments/${assignmentId}/ca-items/`,
    payload,
  )
  return response.data
}

export const updateTeachingAssignmentCaItem = async (
  assignmentId: string,
  itemId: string,
  payload: CaItemWritePayload,
): Promise<CaItem> => {
  const response = await api.patch<CaItem>(
    `/academics/teaching-assignments/${assignmentId}/ca-items/${itemId}/`,
    payload,
  )
  return response.data
}

export const deleteTeachingAssignmentCaItem = async (
  assignmentId: string,
  itemId: string,
): Promise<void> => {
  await api.delete(`/academics/teaching-assignments/${assignmentId}/ca-items/${itemId}/`)
}

export const saveTeachingAssignmentMarks = async (
  assignmentId: string,
  payload: SaveMarksPayload,
): Promise<AssessmentWorkspace> => {
  const response = await api.put<AssessmentWorkspace>(
    `/academics/teaching-assignments/${assignmentId}/marks/`,
    payload,
  )
  return response.data
}

export const publishTeachingAssignmentStudents = async (
  assignmentId: string,
  studentIds: string[],
): Promise<AssessmentWorkspace> => {
  const response = await api.post<AssessmentWorkspace>(
    `/academics/teaching-assignments/${assignmentId}/publish/`,
    { student_ids: studentIds },
  )
  return response.data
}

export const unpublishTeachingAssignmentStudents = async (
  assignmentId: string,
  studentIds: string[],
): Promise<AssessmentWorkspace> => {
  const response = await api.post<AssessmentWorkspace>(
    `/academics/teaching-assignments/${assignmentId}/unpublish/`,
    { student_ids: studentIds },
  )
  return response.data
}

export const getAdminAssessmentFilterOptions =
  async (): Promise<AdminAssessmentFilterOptions> => {
    const response = await api.get<AdminAssessmentFilterOptions>(
      '/academics/assessments/admin/filter-options/',
    )
    return response.data
  }

export const getAdminAssessmentOverview = async (
  termId?: string,
): Promise<AdminAssessmentOverview> => {
  const response = await api.get<AdminAssessmentOverview>(
    '/academics/assessments/admin/classes/',
    { params: termId ? { term_id: termId } : undefined },
  )
  return response.data
}

export const getAdminAssessmentDetail = async (
  streamId: string,
  termId?: string,
): Promise<AdminAssessmentDetail> => {
  const response = await api.get<AdminAssessmentDetail>(
    `/academics/assessments/admin/classes/${streamId}/`,
    { params: termId ? { term_id: termId } : undefined },
  )
  return response.data
}

export const releaseAdminAssessmentStudents = async (
  streamId: string,
  payload: { student_ids: string[]; remarks?: string },
  termId?: string,
): Promise<AdminAssessmentDetail> => {
  const response = await api.post<AdminAssessmentDetail>(
    `/academics/assessments/admin/classes/${streamId}/release/`,
    payload,
    { params: termId ? { term_id: termId } : undefined },
  )
  return response.data
}

export const getClassTeacherAssessmentOverview =
  async (): Promise<ClassTeacherAssessmentOverview> => {
    const response = await api.get<ClassTeacherAssessmentOverview>(
      '/academics/assessments/my-classes/',
    )
    return response.data
  }

export const getClassTeacherAssessmentDetail = async (
  classTeacherId: string,
): Promise<ClassTeacherAssessmentDetail> => {
  const response = await api.get<ClassTeacherAssessmentDetail>(
    `/academics/assessments/class-teachers/${classTeacherId}/`,
  )
  return response.data
}

export const approveClassTeacherStudents = async (
  classTeacherId: string,
  payload: { student_ids: string[]; remarks?: string },
): Promise<ClassTeacherAssessmentDetail> => {
  const response = await api.post<ClassTeacherAssessmentDetail>(
    `/academics/assessments/class-teachers/${classTeacherId}/approve/`,
    payload,
  )
  return response.data
}
