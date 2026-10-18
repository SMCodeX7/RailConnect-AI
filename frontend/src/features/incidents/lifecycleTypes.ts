import type { ApprovedIncidentInput } from './staffTypes'

export interface AmendIncidentInput {
  expected_version: number
  reason: string
  approved: ApprovedIncidentInput
}

export interface ResolveIncidentInput {
  expected_version: number
  reason: string
  resolution_effective_at: string
}

export interface IncidentLifecycleResult {
  incident_id: string
  originating_report_id: string
  status: 'active' | 'resolved'
  incident_version: number
  current_revision_number: number
  current_revision_id: string
}

export interface IncidentAuditEvent {
  event_id: string
  report_id: string
  incident_id: string | null
  revision_id: string | null
  actor_id: string
  action:
    | 'report_verified'
    | 'report_rejected'
    | 'incident_revised'
    | 'incident_resolved'
  reason: string
  request_id: string
  report_version: number
  incident_version: number | null
  occurred_at: string
}

export interface IncidentAuditHistory {
  report_id: string
  items: IncidentAuditEvent[]
  total: number
  limit: number
  offset: number
}
