import api from '@/app/api/api'
import type { AssessmentConfigResponse, LevelConfigPayload } from './types'
import type { SetupProgressResponse } from '../types/types';

const baseApi = '/schools/setup/assessment'

export const getAssessmentConfig = async () => {
    const response = await api.get<AssessmentConfigResponse>(`${baseApi}/`)
    return response.data
}

export const saveLevelConfig = async (levelId: string, config: LevelConfigPayload) => {
    const response = await api.put<AssessmentConfigResponse>(`${baseApi}/levels/${levelId}/`, config)
    return response.data
}


export const completeAssessmentSetup = async () => {
    const response = await api.post<SetupProgressResponse>(`${baseApi}/complete/`)
    return response.data
}