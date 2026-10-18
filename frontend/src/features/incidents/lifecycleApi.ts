import { getJson, postJson } from '../../shared/api/http'
import type {
  AmendIncidentInput,
  IncidentAuditHistory,
  IncidentLifecycleResult,
  ResolveIncidentInput,
} from './lifecycleTypes'

export function amendIncident(
  incidentId: string,
  input: AmendIncidentInput,
  csrfToken: string,
  signal: AbortSignal,
): Promise<IncidentLifecycleResult> {
  return postJson<IncidentLifecycleResult>(
    `/api/v1/staff/incidents/${encodeURIComponent(incidentId)}/amend`,
    input,
    signal,
    csrfToken,
  )
}

export function resolveIncident(
  incidentId: string,
  input: ResolveIncidentInput,
  csrfToken: string,
  signal: AbortSignal,
): Promise<IncidentLifecycleResult> {
  return postJson<IncidentLifecycleResult>(
    `/api/v1/staff/incidents/${encodeURIComponent(incidentId)}/resolve`,
    input,
    signal,
    csrfToken,
  )
}

export function loadReportAudit(
  reportId: string,
  signal: AbortSignal,
  offset = 0,
  limit = 20,
): Promise<IncidentAuditHistory> {
  const query = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  })

  return getJson<IncidentAuditHistory>(
    `/api/v1/staff/reports/${encodeURIComponent(reportId)}/audit?${query}`,
    signal,
  )
}
