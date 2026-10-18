import { beforeEach, describe, expect, it, vi } from 'vitest'

import { getJson, postJson } from '../../shared/api/http'
import {
  amendIncident,
  loadReportAudit,
  resolveIncident,
} from './lifecycleApi'
import type {
  AmendIncidentInput,
  IncidentLifecycleResult,
} from './lifecycleTypes'

vi.mock('../../shared/api/http', () => ({
  getJson: vi.fn(),
  postJson: vi.fn(),
}))

const result: IncidentLifecycleResult = {
  incident_id: 'incident-id',
  originating_report_id: 'report-id',
  status: 'active',
  incident_version: 2,
  current_revision_number: 2,
  current_revision_id: 'revision-2',
}

describe('Incident lifecycle API', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('sends complete amendment facts, expected version and CSRF token', async () => {
    const input: AmendIncidentInput = {
      expected_version: 1,
      reason: 'Reviewed updated synthetic evidence.',
      approved: {
        run_id: 'run-id',
        scope_kind: 'run',
        departure_stop_sequence: null,
        arrival_stop_sequence: null,
        impact_kind: 'delay',
        estimated_delay_minutes: 30,
        effective_from: '2026-10-18T06:00:00Z',
        effective_until: '2026-10-18T10:00:00Z',
        public_summary: 'Synthetic demonstration delay.',
        evidence_basis: 'Controlled demonstration evidence.',
      },
    }

    vi.mocked(postJson).mockResolvedValue(result)
    const signal = new AbortController().signal

    await expect(
      amendIncident('incident-id', input, 'current-csrf', signal),
    ).resolves.toEqual(result)

    expect(postJson).toHaveBeenCalledWith(
      '/api/v1/staff/incidents/incident-id/amend',
      input,
      signal,
      'current-csrf',
    )
  })

  it('sends resolution effective time and expected version', async () => {
    const input = {
      expected_version: 2,
      reason: 'Synthetic disruption ended.',
      resolution_effective_at: '2026-10-18T08:00:00Z',
    }

    vi.mocked(postJson).mockResolvedValue({
      ...result,
      status: 'resolved',
      incident_version: 3,
    })

    const signal = new AbortController().signal

    await resolveIncident(
      'incident-id',
      input,
      'current-csrf',
      signal,
    )

    expect(postJson).toHaveBeenCalledWith(
      '/api/v1/staff/incidents/incident-id/resolve',
      input,
      signal,
      'current-csrf',
    )
  })

  it('loads audit history using the report reference and pagination', async () => {
    const history = {
      report_id: 'report-id',
      items: [],
      total: 0,
      limit: 20,
      offset: 40,
    }

    vi.mocked(getJson).mockResolvedValue(history)
    const signal = new AbortController().signal

    await expect(
      loadReportAudit('report-id', signal, 40),
    ).resolves.toEqual(history)

    expect(getJson).toHaveBeenCalledWith(
      '/api/v1/staff/reports/report-id/audit?limit=20&offset=40',
      signal,
    )
  })

  it('does not automatically retry a failed resolution', async () => {
    const failure = new Error('Decision could not be confirmed.')
    vi.mocked(postJson).mockRejectedValue(failure)

    await expect(
      resolveIncident(
        'incident-id',
        {
          expected_version: 1,
          reason: 'Synthetic disruption ended.',
          resolution_effective_at: '2026-10-18T08:00:00Z',
        },
        'current-csrf',
        new AbortController().signal,
      ),
    ).rejects.toBe(failure)

    expect(postJson).toHaveBeenCalledTimes(1)
  })
})
