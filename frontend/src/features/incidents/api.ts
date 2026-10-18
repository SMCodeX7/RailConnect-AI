import { restoreStaffSession } from '../auth/api'
import { ApiError, postJson } from '../../shared/api/http'
import type { ReportSubmission, SubmitReportInput } from './types'

export async function submitPassengerReport(
  input: SubmitReportInput,
  signal: AbortSignal,
): Promise<ReportSubmission> {
  let csrfToken: string | undefined

  try {
    const session = await restoreStaffSession(signal)
    csrfToken = session.csrf_token
  } catch (error) {
    if (!(error instanceof ApiError && error.status === 401)) {
      throw error
    }
  }

  if (signal.aborted) {
    throw new DOMException('The request was aborted.', 'AbortError')
  }

  return postJson<ReportSubmission>(
    '/api/v1/reports',
    input,
    signal,
    csrfToken,
  )
}
