import { getJson, postJson } from '../../shared/api/http'
import type {
  PendingReportQueue,
  RejectReportInput,
  ReportReviewResult,
  VerifyReportInput,
} from './staffTypes'

export function loadPendingReports(
  signal: AbortSignal,
  offset = 0,
  limit = 20,
): Promise<PendingReportQueue> {
  const query = new URLSearchParams({
    limit: String(limit),
    offset: String(offset),
  })

  return getJson<PendingReportQueue>(
    `/api/v1/staff/reports?${query}`,
    signal,
  )
}

export function verifyPassengerReport(
  reportId: string,
  input: VerifyReportInput,
  csrfToken: string,
  signal: AbortSignal,
): Promise<ReportReviewResult> {
  return postJson<ReportReviewResult>(
    `/api/v1/staff/reports/${encodeURIComponent(reportId)}/verify`,
    input,
    signal,
    csrfToken,
  )
}

export function rejectPassengerReport(
  reportId: string,
  input: RejectReportInput,
  csrfToken: string,
  signal: AbortSignal,
): Promise<ReportReviewResult> {
  return postJson<ReportReviewResult>(
    `/api/v1/staff/reports/${encodeURIComponent(reportId)}/reject`,
    input,
    signal,
    csrfToken,
  )
}
