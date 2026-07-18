import api from '@/app/api/api'
import type { FeeItem, FeeItemFormValues, FeeStructureResponse } from './types'
import type { SetupProgressResponse } from '../types/types'

const BASE_URL = '/schools/setup/fees';

export const getFeeStructures = async () => {
    const response = await api.get<FeeStructureResponse>(BASE_URL);
    return response.data;
}

export const createFeeItem = async (data: FeeItemFormValues) => {
    const response = await api.post<FeeItem>(`${BASE_URL}/items/`, data);
    return response.data;
}

export const updateFeeItem = async (id: string, data: Partial<FeeItemFormValues>) => {
    const response = await api.patch<FeeItem>(`${BASE_URL}/items/${id}/`, data);
    return response.data;
}

export const deleteFeeItem = async (id: string) => { 
    const response = await api.delete(`${BASE_URL}/items/${id}/`);
    return response.data;
}

export const completeFeeSetup = async () => {
    const response = await api.post<SetupProgressResponse>(`${BASE_URL}/complete/`);
    return response.data;
}

// These will probably be moved to a different file in the future

export const getClasses = async () => {
    const response = await api.get<{name: string, id: string}[]>('/academics/class-levels/');
    return response.data;
}

export const getLevels = async () => {
    const response = await api.get<{name: string, id: string}[]>('/academics/levels/');
    return response.data;
}