import api from "@/app/api/api";
import type { AddClassPayload, AddStreamPayload, AddSubjectGroupResponse, AddSubjectPayload, AddSubjectResponse } from "./class-subject-setup-types";
import type { ClassForSetup, ClassSubjectForSetup, StreamForSetup } from "./types";

const basePath = '/schools/setup/classes-and-subjects/'


// Subject
export const addSubject = async (payload: AddSubjectPayload) => {
    const response = await api.post<AddSubjectResponse>(basePath + 'subjects/', payload)
    return response.data
}

export const editSubject = async (subjectId: string, payload: Omit<AddSubjectPayload, 'level_id'>) => {
    const response = await api.patch<AddSubjectResponse>(basePath + 'subjects/' + subjectId + '/', payload)
    return response.data
}

export const deleteSubject = async (subjectId: string) => {
    const response = await api.delete(basePath + 'subjects/' + subjectId + '/')
    return response.data
}

export const activateOrDeactivateSubject = async (subjectId: string, isActive: boolean) => {
    const response = await api.patch(basePath + 'subjects/' + subjectId + '/status/', {
        is_active: isActive
    })
    return response.data
}

// Subject Group
export const addSubjectGroup = async (levelId: string, subjectId: string, payload: {name: string}) => {
    const response = await api.post<AddSubjectGroupResponse>(basePath + 'levels/' + levelId + '/subjects/' + subjectId + '/groups/', payload)
    return response.data
}

export const editSubjectGroup = async (groupId: string, payload: {name: string}) => {
    const response = await api.patch<AddSubjectGroupResponse>(basePath + 'groups/' + groupId + '/', payload)
    return response.data
}

export const deleteSubjectGroup = async (groupId: string) => {
    const response = await api.delete(basePath + 'groups/' + groupId + '/')
    return response.data
}

// Class
export const addClass = async (levelId: string, payload: AddClassPayload) => {
    const response = await api.post<ClassForSetup>(basePath + 'levels/' + levelId + '/classes/', payload)
    return response.data
}

export const editClass = async (classId: string, payload: Partial<AddClassPayload>) => {
    const response = await api.patch<ClassForSetup>(basePath + 'classes/' + classId + '/', payload)
    return response.data
}

export const deleteClass = async (classId: string) => {
    const response = await api.delete(basePath + 'classes/' + classId + '/')
    return response.data
}

export const activateOrDeactivateClass = async (classId: string, isActive: boolean) => {
    const response = await api.patch(basePath + 'classes/' + classId + '/status/', {
        is_active: isActive
    })
    return response.data
}

export const assignSubjectToClass = async (classId: string, subjectId: string) => {
    const response = await api.post<ClassSubjectForSetup>(basePath + 'classes/' + classId + '/subjects/' + subjectId + '/')
    return response.data
}

export const removeSubjectFromClass = async (classId: string, subjectId: string) => {
    const response = await api.delete(basePath + 'classes/' + classId + '/subjects/' + subjectId + '/')
    return response.data
}

// Streams

export const addStream = async (classId: string, payload: AddStreamPayload) => {
    const response = await api.post<StreamForSetup>(basePath + 'classes/' + classId + '/streams/', payload)
    return response.data
}

export const editStream = async (streamId: string, payload: Partial<AddStreamPayload>) => {
    const response = await api.patch<StreamForSetup>(basePath + 'streams/' + streamId + '/', payload)
    return response.data
}

export const deleteStream = async (streamId: string) => {
    const response = await api.delete(basePath + 'streams/' + streamId + '/')
    return response.data
}


// levels
export const activateOrDeactivateLevel = async (levelId: string, isActive: boolean) => {
    const response = await api.patch(basePath + 'levels/' + levelId + '/status/', {
        is_active: isActive
    })
    return response.data
}