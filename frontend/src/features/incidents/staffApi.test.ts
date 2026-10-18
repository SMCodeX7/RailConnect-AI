import { beforeEach, describe, expect, it, vi } from 'vitest'

import { getJson, postJson } from '../../shared/api/http'
import {
  loadPendingReports,
  rejectPassengerReport,
  verifyPassengerReport,
} from './staffApi'
import type { VerifyReportInput } from './staffTypes'

vi.mock('../../shared/api/http', () => ({
  getJson: vi.fn(),
  postJson: vi.fn(),
}))

describe('Staff incident API', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('requests a bounded queue page', async () => {
    const page = {
      items: [],
      total: 0,
      limit: 20,
      offset: 40,
    }
    vi.mocked(getJson).mockResolvedValue(page)
    const controller = new AbortController()

    const result = await loadPendingReports(controller.signal, 40)

    expect(result).toEqual(page)
    expect(getJson).toHaveBeenCalledWith(
      '/api/v1/staff/reports?limit=20&offset=40',
      controller.signal,
    )
  })

  it('sends the expected report version and CSRF token for rejection', async () => {
    const input = {
      expected_version: 3,
      reason: 'Synthetic evidence is insufficient.',
    }
    vi.mocked(postJson).mockResolvedValue({
      report_id: 'report-id',
      status: 'rejected',
      report_version: 4,
      incident_id: null,
      revision_id: null,
      incident_version: null,
    })
    const controller = new AbortController()

    await rejectPassengerReport(
      'report-id',
      input,
      'current-csrf',
      controller.signal,
    )

    expect(postJson).toHaveBeenCalledWith(
      '/api/v1/staff/reports/report-id/reject',
      input,
      controller.signal,
      'current-csrf',
    )
  })

  it('sends independently approved facts for verification', async () => {
    const input: VerifyReportInput = {
      expected_version: 1,
      reason: 'Reviewed synthetic evidence.',
      approved: {
        run_id: 'prepared-run-id',
        scope_kind: 'segment',
        departure_stop_sequence: 1,
        arrival_stop_sequence: 2,
        impact_kind: 'delay',
        estimated_delay_minutes: 15,
        effective_from: '2026-10-18T06:00:00Z',
        effective_until: '2026-10-18T10:00:00Z',
        public_summary: 'Synthetic demonstration delay.',
        evidence_basis: 'Controlled demonstration evidence.',
      },
    }
    vi.mocked(postJson).mockResolvedValue({
      report_id: 'report-id',
      status: 'verified',
      report_version: 2,
      incident_id: 'incident-id',
      revision_id: 'revision-id',
      incident_version: 1,
    })
    const controller = new AbortController()

    await verifyPassengerReport(
      'report-id',
      input,
      'current-csrf',
      controller.signal,
    )

    expect(postJson).toHaveBeenCalledWith(
      '/api/v1/staff/reports/report-id/verify',
      input,
      controller.signal,
      'current-csrf',
    )
  })

  it('propagates conflicts without automatically retrying a decision', async () => {
    const conflict = new Error('Version conflict.')
    vi.mocked(postJson).mockRejectedValue(conflict)

    await expect(
      rejectPassengerReport(
        'report-id',
        {
          expected_version: 1,
          reason: 'Reviewed synthetic claim.',
        },
        'current-csrf',
        new AbortController().signal,
      ),
    ).rejects.toBe(conflict)

    expect(postJson).toHaveBeenCalledTimes(1)
  })
})
