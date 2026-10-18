import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError, postJson } from '../../shared/api/http'
import { restoreStaffSession } from '../auth/api'
import { submitPassengerReport } from './api'

vi.mock('../../shared/api/http', async (importOriginal) => {
  const actual =
    await importOriginal<typeof import('../../shared/api/http')>()

  return {
    ...actual,
    postJson: vi.fn(),
  }
})

vi.mock('../auth/api', () => ({
  restoreStaffSession: vi.fn(),
}))

const input = {
  title: 'Synthetic passenger report',
  narrative: 'A fictional observation for the portfolio pilot.',
  observed_at: '2026-10-17T06:00:00.000Z',
}

const receipt = {
  report_id: 'synthetic-report-id',
  status: 'pending' as const,
  submitted_at: '2026-10-18T06:00:00Z',
  message: 'Report received.',
}

describe('Passenger report API', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('submits without CSRF when session restoration returns 401', async () => {
    vi.mocked(restoreStaffSession).mockRejectedValue(
      new ApiError(
        'Authentication is required.',
        401,
        'UNAUTHENTICATED',
        null,
        null,
      ),
    )
    vi.mocked(postJson).mockResolvedValue(receipt)

    const controller = new AbortController()
    const result = await submitPassengerReport(
      input,
      controller.signal,
    )

    expect(result).toEqual(receipt)
    expect(postJson).toHaveBeenCalledWith(
      '/api/v1/reports',
      input,
      controller.signal,
      undefined,
    )
  })

  it('uses the current staff session CSRF token', async () => {
    vi.mocked(restoreStaffSession).mockResolvedValue({
      actor: {
        user_id: 'synthetic-staff-id',
        username: 'synthetic_controller',
        display_name: 'Synthetic Controller',
        roles: ['controller'],
        permissions: ['reports.read', 'reports.review'],
      },
      csrf_token: 'synthetic-csrf-token',
      expires_at: '2026-10-18T14:00:00Z',
    })
    vi.mocked(postJson).mockResolvedValue(receipt)

    const controller = new AbortController()

    await submitPassengerReport(input, controller.signal)

    expect(postJson).toHaveBeenCalledWith(
      '/api/v1/reports',
      input,
      controller.signal,
      'synthetic-csrf-token',
    )
  })

  it('does not submit when the session check fails unexpectedly', async () => {
    const failure = new Error('Session service unavailable.')
    vi.mocked(restoreStaffSession).mockRejectedValue(failure)

    await expect(
      submitPassengerReport(input, new AbortController().signal),
    ).rejects.toBe(failure)

    expect(postJson).not.toHaveBeenCalled()
  })

  it('does not submit after cancellation', async () => {
    vi.mocked(restoreStaffSession).mockResolvedValue({
      actor: {
        user_id: 'synthetic-staff-id',
        username: 'synthetic_controller',
        display_name: 'Synthetic Controller',
        roles: ['controller'],
        permissions: ['reports.read'],
      },
      csrf_token: 'synthetic-csrf-token',
      expires_at: '2026-10-18T14:00:00Z',
    })

    const controller = new AbortController()
    controller.abort()

    await expect(
      submitPassengerReport(input, controller.signal),
    ).rejects.toMatchObject({ name: 'AbortError' })

    expect(postJson).not.toHaveBeenCalled()
  })
})
