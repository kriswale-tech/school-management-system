import api from '@/app/api/api'
import type { PaginatedResponse } from '@/types/generalTypes'
import type {
  ClassTeacherAssignment,
  CreateClassTeacherAssignmentPayload,
  CreateTeachingAssignmentPayload,
  Teacher,
  TeachingAssignment,
} from './types'
import type { SetupProgressResponse } from '../types/types';

const baseUrl = '/schools/setup/teachers/'

export const getTeachers = async (page = 1): Promise<PaginatedResponse<Teacher>> => {
  const response = await api.get<PaginatedResponse<Teacher>>(baseUrl, {
    params: { page },
  })
  return response.data
}

export const createClassTeacherAssignment = async (
  data: CreateClassTeacherAssignmentPayload,
): Promise<ClassTeacherAssignment> => {
  const response = await api.post<ClassTeacherAssignment>(
    `${baseUrl}class-teacher-assignments/`,
    data,
  )
  return response.data
}

export const deleteClassTeacherAssignment = async (assignmentId: string): Promise<void> => {
  await api.delete(`${baseUrl}class-teacher-assignments/${assignmentId}/`)
}

export const createTeachingAssignment = async (
  data: CreateTeachingAssignmentPayload,
): Promise<TeachingAssignment> => {
  const response = await api.post<TeachingAssignment>(`${baseUrl}teaching-assignments/`, data)
  return response.data
}

export const deleteTeachingAssignment = async (assignmentId: string): Promise<void> => {
  await api.delete(`${baseUrl}teaching-assignments/${assignmentId}/`)
}


export const completeTeacherSetup = async (): Promise<SetupProgressResponse> => {
  const response = await api.post<SetupProgressResponse>(`${baseUrl}complete/`)
  return response.data
}