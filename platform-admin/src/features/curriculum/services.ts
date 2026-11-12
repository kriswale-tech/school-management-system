import api from '@/lib/api'

export type CurriculumSubject = { lineage_id: string; name: string }

export type CurriculumClass = {
  lineage_id: string
  name: string
  order: number
  subjects: CurriculumSubject[]
}

export type CurriculumLevel = {
  lineage_id: string
  name: string
  description: string
  order: number
  subject_scope: 'level' | 'class'
  allows_custom_classes: boolean
  classes: CurriculumClass[]
  subjects: CurriculumSubject[]
}

export type CurriculumVersion = {
  id: string
  name: string
  code: string
  version: string
  status: 'draft' | 'published'
  is_active: boolean
  published_at: string | null
  levels: CurriculumLevel[]
  school_count?: number
}

export type CurriculumOverview = {
  active: CurriculumVersion | null
  draft: CurriculumVersion | null
  versions: CurriculumVersion[]
  schools_behind: Array<{ id: string; name: string; version: string }>
}

export type AdoptionChange = { action: string; kind: string; summary: string }

export type AdoptionPlan = {
  up_to_date: boolean
  from_version: string | null
  to_version: string
  changes: AdoptionChange[]
  applies_on?: 'next_term' | 'now'
  scheduled?: boolean
  applied?: boolean
  summary?: string
}

export async function getCurriculum() {
  const { data } = await api.get<CurriculumOverview>('/platform/curriculum/')
  return data
}

export async function startCurriculumDraft() {
  const { data } = await api.post<CurriculumVersion>('/platform/curriculum/draft/')
  return data
}

export async function saveCurriculumDraft(id: string, version: string, levels: CurriculumLevel[]) {
  const { data } = await api.put<CurriculumVersion>(`/platform/curriculum/${id}/`, {
    version,
    levels,
  })
  return data
}

export async function publishCurriculum(id: string) {
  const { data } = await api.post<{ curriculum: CurriculumVersion; schools_alerted: number }>(
    `/platform/curriculum/${id}/`,
  )
  return data
}

export async function getSchoolAdoption(schoolId: string) {
  const { data } = await api.get<AdoptionPlan>(`/platform/schools/${schoolId}/curriculum-adoption/`)
  return data
}

export async function adoptSchoolCurriculum(schoolId: string) {
  const { data } = await api.post<AdoptionPlan>(`/platform/schools/${schoolId}/curriculum-adoption/`)
  return data
}
