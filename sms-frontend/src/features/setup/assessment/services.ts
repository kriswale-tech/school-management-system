import api from '@/app/api/api'
import { getQueryUrl } from '@/utils/get-query-url'
import type {
  AssessmentConfigResponse,
  AssessmentSettingsResponse,
  LevelConfigPayload,
} from './types'
import type { SetupProgressResponse } from '../types/types'

const baseApi = '/schools/setup/assessment'
const settingsApi = '/academics/assessments/settings'

export const getAssessmentConfig = async () => {
  const response = await api.get<AssessmentConfigResponse>(`${baseApi}/`)
  return response.data
}

export const saveLevelConfig = async (
  levelId: string,
  config: LevelConfigPayload,
  termId?: string,
) => {
  if (termId) {
    const response = await api.put(
      getQueryUrl(`${settingsApi}/levels/${levelId}/`, { term_id: termId }),
      config,
    )
    return response.data
  }
  const response = await api.put(`${baseApi}/levels/${levelId}/`, config)
  return response.data
}

export const getAssessmentSettings = async (termId?: string) => {
  const response = await api.get<AssessmentSettingsResponse>(
    getQueryUrl(`${settingsApi}/`, { term_id: termId }),
  )
  return response.data
}

export const completeAssessmentSetup = async () => {
  const response = await api.post<SetupProgressResponse>(`${baseApi}/complete/`)
  return response.data
}
