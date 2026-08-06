export interface AddSubjectPayload {
level_id: string
name: string
class_ids?: string[]
}

export interface AddSubjectResponse {
    id: string
    name: string
    is_active: boolean
    is_system_generated: boolean
    is_editable: boolean
    class_ids: string[]
    assigned_classes: {
        class_id: string
        class_name: string
        class_subject_id: string
    }[]
}

export interface AddSubjectGroupResponse {
    id: string
    name: string
    is_active: boolean
}

export interface AddClassPayload {
    name: string
    description?: string
    order?: number
}

export interface AddStreamPayload {
    name: string
    description?: string
}

