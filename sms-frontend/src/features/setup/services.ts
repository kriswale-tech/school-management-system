import api from '@/app/api/api'
import type {
  Setup,
  SchoolProfile,
  SetupProgressResponse,
  AcademicYearAndTerm,
  AcademicYearAndTermPayload,
  LevelWithRelatedClassesAndSubjects,
} from './types'

// get setup endpoint
export const getSetup = async () => {
  const response = await api.get<Setup>('/schools/setup/')
  return response.data
}

// get school profile endpoint
export const getSchoolProfile = async () => {
  const response = await api.get<SchoolProfile>('/schools/school/')
  return response.data
}

// update school profile endpoint
export const setupSchoolProfile = async (payload: FormData) => {
  const response = await api.post<SetupProgressResponse>('/schools/setup/school-profile/', payload)
  return response.data
}

// get academic year and term endpoint
export const getAcademicYearAndTerm = async () => {
  const response = await api.get<AcademicYearAndTerm>('/schools/setup/academic-year-term/')
  return response.data
}

// update academic year and term endpoint
export const updateAcademicYearAndTerm = async (payload: AcademicYearAndTermPayload) => {
  const response = await api.post<SetupProgressResponse>(
    '/schools/setup/academic-year-term/',
    payload,
  )
  return response.data
}

// get levels with related classes and subjects endpoint
export const getClassAndSubjects = async () => {
  const response = await api.get<LevelWithRelatedClassesAndSubjects>(
    '/schools/setup/classes-and-subjects/',
  )
  return response.data
}
