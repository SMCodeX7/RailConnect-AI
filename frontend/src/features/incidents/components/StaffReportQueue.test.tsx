import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import type { StaffSession } from '../../auth/types'
import { ApiError } from '../../../shared/api/http'
import {
  loadPendingReports,
  rejectPassengerReport,
  verifyPassengerReport,
} from '../staffApi'
import type {
  PendingReport,
  PendingReportQueue,
} from '../staffTypes'
import { StaffReportQueue } from './StaffReportQueue'

vi.mock('../staffApi', () => ({
  loadPendingReports: vi.fn(),
  rejectPassengerReport: vi.fn(),
  verifyPassengerReport: vi.fn(),
}))

const session: StaffSession = {
  actor: {
    user_id: 'synthetic-controller-id',
    username: 'synthetic_controller',
    display_name: 'Synthetic Controller',
    roles: ['controller'],
    permissions: ['reports.read', 'reports.review'],
  },
  csrf_token: 'synthetic-current-csrf',
  expires_at: '2099-01-01T00:00:00Z',
}

const report: PendingReport = {
  report_id: 'synthetic-report-id',
  title: 'Synthetic station report',
  narrative: 'An unverified synthetic observation.',
  observed_at: '2026-10-18T05:00:00Z',
  submitted_at: '2026-10-18T05:05:00Z',
  run_hint_id: 'synthetic-prepared-run-id',
  station_hint_id: null,
  departure_stop_sequence_hint: null,
  arrival_stop_sequence_hint: null,
  status: 'pending',
  version: 3,
}

const page: PendingReportQueue = {
  items: [report],
  total: 1,
  limit: 20,
  offset: 0,
}

const emptyPage: PendingReportQueue = {
  items: [],
  total: 0,
  limit: 20,
  offset: 0,
}

function renderQueue(currentSession = session) {
  const onSessionInvalid = vi.fn()

  const view = render(
    <StaffReportQueue
      session={currentSession}
      onSessionInvalid={onSessionInvalid}
    />,
  )

  return { ...view, onSessionInvalid }
}

async function openReview() {
  const user = userEvent.setup()

  await user.click(
    screen.getByRole('button', { name: 'Load pending reports' }),
  )

  await user.click(
    await screen.findByRole('button', {
      name: 'Open report review',
    }),
  )

  return user
}

function fillVerification() {
  fireEvent.change(screen.getByLabelText('Decision'), {
    target: { value: 'verify' },
  })

  fireEvent.change(screen.getByLabelText('Decision reason'), {
    target: { value: 'Independently reviewed synthetic evidence.' },
  })

  fireEvent.change(screen.getByLabelText('Approved impact'), {
    target: { value: 'delay' },
  })

  fireEvent.change(
    screen.getByLabelText('Approved estimated delay in minutes'),
    {
      target: { value: '25' },
    },
  )

  fireEvent.change(
    screen.getByLabelText(/Effective start/),
    {
      target: { value: '2026-10-18T10:30' },
    },
  )

  fireEvent.change(
    screen.getByLabelText(/Effective end/),
    {
      target: { value: '2026-10-18T14:30' },
    },
  )

  fireEvent.change(
    screen.getByLabelText('Approved public summary'),
    {
      target: { value: 'Synthetic demonstration delay.' },
    },
  )

  fireEvent.change(screen.getByLabelText('Private evidence basis'), {
    target: { value: 'Controlled demonstration evidence.' },
  })

  fireEvent.click(
    screen.getByRole('checkbox', {
      name: /I independently reviewed/,
    }),
  )
}

describe('Staff report queue', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    vi.mocked(loadPendingReports).mockResolvedValue(page)
  })

  it('loads only when requested and displays the empty state', async () => {
    vi.mocked(loadPendingReports).mockResolvedValue(emptyPage)
    const user = userEvent.setup()

    renderQueue()

    expect(loadPendingReports).not.toHaveBeenCalled()

    await user.click(
      screen.getByRole('button', { name: 'Load pending reports' }),
    )

    expect(
      await screen.findByText('No pending reports on this page.'),
    ).toBeInTheDocument()

    expect(loadPendingReports).toHaveBeenCalledWith(
      expect.any(AbortSignal),
      0,
    )
  })

  it('recovers from a queue-loading failure', async () => {
    vi.mocked(loadPendingReports)
      .mockRejectedValueOnce(new Error('Unavailable.'))
      .mockResolvedValueOnce(page)

    const user = userEvent.setup()
    renderQueue()

    await user.click(
      screen.getByRole('button', { name: 'Load pending reports' }),
    )

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Unable to load passenger reports.',
    )

    await user.click(
      screen.getByRole('button', { name: 'Reload report queue' }),
    )

    expect(
      await screen.findByRole('heading', {
        name: 'Synthetic station report',
      }),
    ).toBeInTheDocument()

    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('disables loading while a request is pending', async () => {
    vi.mocked(loadPendingReports).mockImplementation(
      () => new Promise<PendingReportQueue>(() => {}),
    )

    renderQueue()

    fireEvent.click(
      screen.getByRole('button', { name: 'Load pending reports' }),
    )

    expect(
      screen.getByRole('button', { name: 'Reload report queue' }),
    ).toBeDisabled()

    expect(
      screen.getByText('Working on the report queue…'),
    ).toBeInTheDocument()

    expect(loadPendingReports).toHaveBeenCalledTimes(1)
  })

  it('shows the narrative and labels passenger scope hints as unverified', async () => {
    const user = userEvent.setup()
    renderQueue()

    await user.click(
      screen.getByRole('button', { name: 'Load pending reports' }),
    )

    expect(
      await screen.findByText('An unverified synthetic observation.'),
    ).toBeInTheDocument()

    expect(
      screen.getByText('Unverified run hint'),
    ).toBeInTheDocument()

    expect(
      screen.getByText('synthetic-prepared-run-id'),
    ).toBeInTheDocument()

    expect(
      screen.getByText('Unverified station hint'),
    ).toBeInTheDocument()

    expect(
      screen.getByText('Unverified segment hint'),
    ).toBeInTheDocument()
  })

  it('rejects using the displayed version and current CSRF token, then reloads', async () => {
    vi.mocked(loadPendingReports)
      .mockResolvedValueOnce(page)
      .mockResolvedValueOnce(emptyPage)

    vi.mocked(rejectPassengerReport).mockResolvedValue({
      report_id: report.report_id,
      status: 'rejected',
      report_version: 4,
      incident_id: null,
      revision_id: null,
      incident_version: null,
    })

    renderQueue()
    const user = await openReview()

    await user.type(
      screen.getByLabelText('Decision reason'),
      'Insufficient synthetic evidence.',
    )

    await user.click(
      screen.getByRole('button', { name: 'Reject report' }),
    )

    expect(
      await screen.findByText(
        'Report rejected. The decision was recorded.',
      ),
    ).toBeInTheDocument()

    expect(rejectPassengerReport).toHaveBeenCalledWith(
      report.report_id,
      {
        expected_version: 3,
        reason: 'Insufficient synthetic evidence.',
      },
      session.csrf_token,
      expect.any(AbortSignal),
    )

    expect(
      await screen.findByText('No pending reports on this page.'),
    ).toBeInTheDocument()

    expect(loadPendingReports).toHaveBeenCalledTimes(2)
  })

  it('verifies explicitly approved facts and converts Sri Lanka times to UTC', async () => {
    vi.mocked(loadPendingReports)
      .mockResolvedValueOnce(page)
      .mockResolvedValueOnce(emptyPage)

    vi.mocked(verifyPassengerReport).mockResolvedValue({
      report_id: report.report_id,
      status: 'verified',
      report_version: 4,
      incident_id: 'synthetic-incident-id',
      revision_id: 'synthetic-revision-id',
      incident_version: 1,
    })

    renderQueue()
    const user = await openReview()
    fillVerification()

    await user.click(
      screen.getByRole('button', { name: 'Verify report' }),
    )

    expect(
      await screen.findByText(
        'Report verified. Incident reference: synthetic-incident-id.',
      ),
    ).toBeInTheDocument()

    expect(verifyPassengerReport).toHaveBeenCalledWith(
      report.report_id,
      {
        expected_version: 3,
        reason: 'Independently reviewed synthetic evidence.',
        approved: {
          run_id: report.run_hint_id,
          scope_kind: 'run',
          departure_stop_sequence: null,
          arrival_stop_sequence: null,
          impact_kind: 'delay',
          estimated_delay_minutes: 25,
          effective_from: '2026-10-18T05:00:00.000Z',
          effective_until: '2026-10-18T09:00:00.000Z',
          public_summary: 'Synthetic demonstration delay.',
          evidence_basis: 'Controlled demonstration evidence.',
        },
      },
      session.csrf_token,
      expect.any(AbortSignal),
    )

    expect(loadPendingReports).toHaveBeenCalledTimes(2)
  })

  it('blocks another decision after a version conflict until the queue reloads', async () => {
    vi.mocked(rejectPassengerReport).mockRejectedValue(
      new ApiError(
        'Conflict.',
        409,
        'CONFLICT',
        null,
        null,
      ),
    )

    renderQueue()
    const user = await openReview()

    await user.type(
      screen.getByLabelText('Decision reason'),
      'Reviewed synthetic claim.',
    )

    await user.click(
      screen.getByRole('button', { name: 'Reject report' }),
    )

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'This report changed or was already reviewed.',
    )

    expect(
      screen.getByRole('button', { name: 'Reject report' }),
    ).toBeDisabled()

    expect(rejectPassengerReport).toHaveBeenCalledTimes(1)

    await user.click(
      screen.getByRole('button', { name: 'Reload report queue' }),
    )

    expect(
      await screen.findByRole('button', {
        name: 'Open report review',
      }),
    ).toBeEnabled()

    expect(
      screen.queryByRole('heading', {
        name: 'Review selected report',
      }),
    ).not.toBeInTheDocument()
  })

  it('requests session restoration when the server returns 401', async () => {
    vi.mocked(loadPendingReports).mockRejectedValue(
      new ApiError(
        'Authentication is required.',
        401,
        'UNAUTHENTICATED',
        null,
        null,
      ),
    )

    const user = userEvent.setup()
    const { onSessionInvalid } = renderQueue()

    await user.click(
      screen.getByRole('button', { name: 'Load pending reports' }),
    )

    await waitFor(() => {
      expect(onSessionInvalid).toHaveBeenCalledTimes(1)
    })
  })

  it('allows read-only staff to inspect reports without submitting decisions', async () => {
    const readOnlySession: StaffSession = {
      ...session,
      actor: {
        ...session.actor,
        permissions: ['reports.read'],
      },
    }

    renderQueue(readOnlySession)
    await openReview()

    expect(
      screen.getByText(
        'You have permission to read reports, but not to decide them.',
      ),
    ).toBeInTheDocument()

    expect(
      screen.getByRole('button', { name: 'Reject report' }),
    ).toBeDisabled()

    expect(verifyPassengerReport).not.toHaveBeenCalled()
    expect(rejectPassengerReport).not.toHaveBeenCalled()
  })

  it('moves between queue pages using the returned pagination values', async () => {
    const secondReport: PendingReport = {
      ...report,
      report_id: 'second-report-id',
      title: 'Second synthetic report',
    }

    vi.mocked(loadPendingReports)
      .mockResolvedValueOnce({
        items: [report],
        total: 2,
        limit: 1,
        offset: 0,
      })
      .mockResolvedValueOnce({
        items: [secondReport],
        total: 2,
        limit: 1,
        offset: 1,
      })
      .mockResolvedValueOnce({
        items: [report],
        total: 2,
        limit: 1,
        offset: 0,
      })

    const user = userEvent.setup()
    renderQueue()

    await user.click(
      screen.getByRole('button', { name: 'Load pending reports' }),
    )

    await user.click(
      await screen.findByRole('button', {
        name: 'Next report page',
      }),
    )

    expect(
      await screen.findByRole('heading', {
        name: 'Second synthetic report',
      }),
    ).toBeInTheDocument()

    expect(loadPendingReports).toHaveBeenNthCalledWith(
      2,
      expect.any(AbortSignal),
      1,
    )

    await user.click(
      screen.getByRole('button', {
        name: 'Previous report page',
      }),
    )

    expect(
      await screen.findByRole('heading', {
        name: 'Synthetic station report',
      }),
    ).toBeInTheDocument()

    expect(loadPendingReports).toHaveBeenNthCalledWith(
      3,
      expect.any(AbortSignal),
      0,
    )
  })

  it('aborts a queue request when unmounted', () => {
    vi.mocked(loadPendingReports).mockImplementation(
      () => new Promise<PendingReportQueue>(() => {}),
    )

    const { unmount } = renderQueue()

    fireEvent.click(
      screen.getByRole('button', { name: 'Load pending reports' }),
    )

    const signal = vi.mocked(loadPendingReports).mock.calls[0][0]

    expect(signal.aborted).toBe(false)
    unmount()
    expect(signal.aborted).toBe(true)
  })

  it('preserves a confirmed decision when the subsequent queue refresh fails', async () => {
    vi.mocked(loadPendingReports)
      .mockResolvedValueOnce(page)
      .mockRejectedValueOnce(new Error('Queue temporarily unavailable.'))

    vi.mocked(rejectPassengerReport).mockResolvedValue({
      report_id: report.report_id,
      status: 'rejected',
      report_version: 4,
      incident_id: null,
      revision_id: null,
      incident_version: null,
    })

    renderQueue()
    const user = await openReview()

    await user.type(
      screen.getByLabelText('Decision reason'),
      'Insufficient synthetic evidence.',
    )

    await user.click(
      screen.getByRole('button', { name: 'Reject report' }),
    )

    expect(
      await screen.findByText(
        'Report rejected. The decision was recorded.',
      ),
    ).toBeInTheDocument()

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Unable to load passenger reports.',
    )

    expect(rejectPassengerReport).toHaveBeenCalledTimes(1)
  })

  it('rejects an effective end that does not follow the start', async () => {
    renderQueue()
    const user = await openReview()
    fillVerification()

    fireEvent.change(
      screen.getByLabelText(/Effective end/),
      {
        target: { value: '2026-10-18T09:30' },
      },
    )

    await user.click(
      screen.getByRole('button', { name: 'Verify report' }),
    )

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'The end must follow the start.',
    )

    expect(verifyPassengerReport).not.toHaveBeenCalled()
  })
})
