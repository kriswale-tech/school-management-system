import api from '@/app/api/api'
import type { SetupProgressResponse } from '../types/types'
import type { AcademicYearAndTerm, AcademicYearAndTermPayload } from './types'

export const getAcademicYearAndTerm = async () => {
  const response = await api.get<AcademicYearAndTerm>('/schools/setup/academic-year-term/')
  return response.data
}

export const updateAcademicYearAndTerm = async (payload: AcademicYearAndTermPayload) => {
  const response = await api.post<SetupProgressResponse>(
    '/schools/setup/academic-year-term/',
    payload,
  )
  return response.data
}
