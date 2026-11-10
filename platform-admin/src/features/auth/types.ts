export type PlatformRole =
  | 'super_admin'
  | 'operations'
  | 'finance'
  | 'support'
  | 'curriculum'

export type PlatformUser = {
  id: string
  email: string
  first_name: string
  last_name: string
  full_name: string
  role: PlatformRole
  mfa_enabled: boolean
  is_active: boolean
  created_at: string
}

export type LoginResponse = {
  mfa_required: boolean
  mfa_token?: string
  user: PlatformUser
}

export type PlatformSettings = {
  id: string
  public_school_registration_enabled: boolean
  subscription_grace_days: number
  updated_at: string
}
