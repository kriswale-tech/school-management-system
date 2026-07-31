export type ClassEntry = {
  id: string
  class_level_id: string
  display_name: string
  student_count: number
  is_default: boolean
}

export type AllClassesLevel = {
  id: string
  name: string
  order: number
  classes: ClassEntry[]
}

export type AllClassesResponse = {
  term_id: string
  levels: AllClassesLevel[]
}

export type AllClassesQueryParams = {
  term?: string
}
