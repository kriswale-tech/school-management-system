export interface Step {
  step: string
  name: string
  completed: boolean
  required: boolean
}

export interface Setup {
  id: number
  steps: Step[]
  current_step: string
  progress_percentage: number
  started_at: string
  completed_at: string
  updated_at: string
  school: string
}

export interface SetupProgressResponse {
  next_step: string
  completed_steps: string[]
  is_complete: boolean
  progress_percentage: number
}
