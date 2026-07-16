import api from '@/app/api/api'
import type { SetupProgressResponse } from '../types/types'
import type { LevelWithRelatedClassesAndSubjects } from './types'

export const getClassAndSubjects = async () => {
  const response = await api.get<LevelWithRelatedClassesAndSubjects>(
    '/schools/setup/classes-and-subjects/',
  )
  return response.data
}

export const updateClassAndSubjectsSetup = async () => {
  const response = await api.post<SetupProgressResponse>(
    '/schools/setup/classes-and-subjects/complete/',
  )
  return response.data
}
