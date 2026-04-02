export type UserRole = 'coach' | 'admin'

export type AuthUser = {
  id: number
  email: string
  name: string
  role: UserRole
  avatar_url?: string
}

export type Coach = {
  id: number
  name: string
  email: string
  active_client_count: number
  is_active: boolean
}

export type Account = {
  id: number
  company_name: string
  assigned_coach_id: number
  assigned_coach_name: string
}

export type Client = {
  id: number
  name: string
  email: string
  account_id: number
  account_name: string
  assigned_coach_id: number
  assigned_coach_name: string
}

export type AuditRecord = {
  id: number
  sync_run_id: number
  change_type: 'reassignment' | 'new_assignment' | 'removed'
  client_id: number
  client_name: string
  previous_coach_id: number | null
  previous_coach_name: string | null
  new_coach_id: number | null
  new_coach_name: string | null
  detected_at: string
  transition_brief?: string
}

export type SyncRun = {
  id: number
  triggered_by: string
  started_at: string
  completed_at: string | null
  status: 'running' | 'completed' | 'failed'
  changes_detected: number
}
