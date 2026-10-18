export interface PendingReport {
  report_id: string
  title: string
  narrative: string
  observed_at: string
  submitted_at: string
  run_hint_id: string | null
  station_hint_id: string | null
  departure_stop_sequence_hint: number | null
  arrival_stop_sequence_hint: number | null
  status: 'pending'
  version: number
}

export interface PendingReportQueue {
  items: PendingReport[]
  total: number
  limit: number
  offset: number
}

export interface ApprovedIncidentInput {
  run_id: string
  scope_kind: 'run' | 'segment'
  departure_stop_sequence: number | null
  arrival_stop_sequence: number | null
  impact_kind: 'cancellation' | 'restriction' | 'delay'
  estimated_delay_minutes: number | null
  effective_from: string
  effective_until: string
  public_summary: string
  evidence_basis: string
}

export interface VerifyReportInput {
  expected_version: number
  reason: string
  approved: ApprovedIncidentInput
}

export interface RejectReportInput {
  expected_version: number
  reason: string
}

export interface ReportReviewResult {
  report_id: string
  status: 'verified' | 'rejected'
  report_version: number
  incident_id: string | null
  revision_id: string | null
  incident_version: number | null
}
