export type StaffPermission =
  | 'reports.read'
  | 'reports.review'
  | 'incidents.edit'
  | 'incidents.resolve'
  | 'timetable.manage'
  | 'audit.read'

export interface StaffActor {
  user_id: string
  username: string
  display_name: string
  roles: string[]
  permissions: StaffPermission[]
}

export interface StaffSession {
  actor: StaffActor
  csrf_token: string
  expires_at: string
}

export interface StaffLoginInput {
  username: string
  password: string
}
