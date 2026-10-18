import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '../../../shared/api/http'
import { loadReportAudit } from '../lifecycleApi'
import type {
  IncidentAuditEvent,
  IncidentAuditHistory,
} from '../lifecycleTypes'
import { IncidentAuditPanel } from './IncidentAuditPanel'

vi.mock('../lifecycleApi', () => ({
  loadReportAudit: vi.fn(),
}))

const auditEvent: IncidentAuditEvent = {
  event_id: 'audit-event-1',
  report_id: 'report-reference-1',
  incident_id: 'incident-reference-1',
  revision_id: 'revision-reference-1',
  actor_id: 'staff-reference-1',
  action: 'report_verified',
  reason: 'Reviewed synthetic evidence.',
  request_id: 'request-reference-1',
  report_version: 2,
  incident_version: 1,
  occurred_at: '2026-10-18T06:00:00Z',
}

const history: IncidentAuditHistory = {
  report_id: auditEvent.report_id,
  items: [auditEvent],
  total: 1,
  limit: 20,
  offset: 0,
}

function renderAudit() {
  const onSessionInvalid = vi.fn()

  const view = render(
    <IncidentAuditPanel onSessionInvalid={onSessionInvalid} />,
  )

  return { ...view, onSessionInvalid }
}

async function requestHistory() {
  const user = userEvent.setup()

  await user.type(
    screen.getByLabelText('Report reference for audit'),
    auditEvent.report_id,
  )

  await user.click(
    screen.getByRole('button', { name: 'Load audit history' }),
  )

  return user
}

describe('Incident audit panel', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    vi.mocked(loadReportAudit).mockResolvedValue(history)
  })

  it('waits for an explicit request before loading private history', () => {
    renderAudit()

    expect(
      screen.getByRole('heading', {
        name: 'Private report audit history',
      }),
    ).toBeInTheDocument()

    expect(loadReportAudit).not.toHaveBeenCalled()
  })

  it('loads and displays the selected report audit history', async () => {
    renderAudit()
    await requestHistory()

    expect(
      await screen.findByRole('heading', {
        name: 'Report verified',
      }),
    ).toBeInTheDocument()

    expect(loadReportAudit).toHaveBeenCalledWith(
      auditEvent.report_id,
      expect.any(AbortSignal),
      0,
    )

    expect(
      screen.getByText('Reviewed synthetic evidence.'),
    ).toBeInTheDocument()

    expect(
      screen.getByText('staff-reference-1'),
    ).toBeInTheDocument()

    expect(
      screen.getByText('revision-reference-1'),
    ).toBeInTheDocument()

    expect(
      screen.getByText('request-reference-1'),
    ).toBeInTheDocument()
  })

  it('shows an empty audit history without inventing events', async () => {
    vi.mocked(loadReportAudit).mockResolvedValue({
      ...history,
      items: [],
      total: 0,
    })

    renderAudit()
    await requestHistory()

    expect(
      await screen.findByText('No audit events on this page.'),
    ).toBeInTheDocument()

    expect(
      screen.queryByRole('heading', { name: 'Report verified' }),
    ).not.toBeInTheDocument()
  })

  it('supports rejected reports without incident or revision references', async () => {
    vi.mocked(loadReportAudit).mockResolvedValue({
      ...history,
      items: [
        {
          ...auditEvent,
          action: 'report_rejected',
          incident_id: null,
          incident_version: null,
          revision_id: null,
        },
      ],
    })

    renderAudit()
    await requestHistory()

    expect(
      await screen.findByRole('heading', {
        name: 'Report rejected',
      }),
    ).toBeInTheDocument()

    expect(screen.getAllByText('Not applicable')).toHaveLength(3)
  })

  it('displays denied access without showing audit records', async () => {
    vi.mocked(loadReportAudit).mockRejectedValue(
      new ApiError('Forbidden.', 403, 'FORBIDDEN', null, null),
    )

    renderAudit()
    await requestHistory()

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Audit access was denied.',
    )

    expect(
      screen.queryByText('Reviewed synthetic evidence.'),
    ).not.toBeInTheDocument()
  })

  it('requests session restoration after authentication expires', async () => {
    vi.mocked(loadReportAudit).mockRejectedValue(
      new ApiError(
        'Authentication required.',
        401,
        'UNAUTHENTICATED',
        null,
        null,
      ),
    )

    const { onSessionInvalid } = renderAudit()
    await requestHistory()

    await waitFor(() => {
      expect(onSessionInvalid).toHaveBeenCalledTimes(1)
    })
  })

  it('shows a missing-report message', async () => {
    vi.mocked(loadReportAudit).mockRejectedValue(
      new ApiError('Not found.', 404, 'NOT_FOUND', null, null),
    )

    renderAudit()
    await requestHistory()

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'No report exists with that reference.',
    )
  })

  it('allows retry after a loading failure', async () => {
    vi.mocked(loadReportAudit)
      .mockRejectedValueOnce(new Error('Unavailable.'))
      .mockResolvedValueOnce(history)

    renderAudit()
    const user = await requestHistory()

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Unable to load audit history.',
    )

    await user.click(
      screen.getByRole('button', { name: 'Load audit history' }),
    )

    expect(
      await screen.findByRole('heading', { name: 'Report verified' }),
    ).toBeInTheDocument()

    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('clears displayed private history when the report reference changes', async () => {
    renderAudit()
    await requestHistory()

    await screen.findByRole('heading', { name: 'Report verified' })

    fireEvent.change(
      screen.getByLabelText('Report reference for audit'),
      {
        target: { value: 'another-report-reference' },
      },
    )

    expect(
      screen.queryByText('Reviewed synthetic evidence.'),
    ).not.toBeInTheDocument()

    expect(loadReportAudit).toHaveBeenCalledTimes(1)
  })

  it('loads the next audit page using the original report reference', async () => {
    vi.mocked(loadReportAudit)
      .mockResolvedValueOnce({
        ...history,
        total: 2,
        limit: 1,
      })
      .mockResolvedValueOnce({
        ...history,
        items: [
          {
            ...auditEvent,
            event_id: 'audit-event-2',
            action: 'incident_resolved',
            reason: 'Synthetic disruption ended.',
            incident_version: 2,
          },
        ],
        total: 2,
        limit: 1,
        offset: 1,
      })

    renderAudit()
    const user = await requestHistory()

    await user.click(
      await screen.findByRole('button', {
        name: 'Next audit page',
      }),
    )

    expect(
      await screen.findByRole('heading', {
        name: 'Incident resolved',
      }),
    ).toBeInTheDocument()

    expect(loadReportAudit).toHaveBeenNthCalledWith(
      2,
      auditEvent.report_id,
      expect.any(AbortSignal),
      1,
    )

    expect(
      screen.getByRole('button', { name: 'Next audit page' }),
    ).toBeDisabled()

    expect(
      screen.getByRole('button', { name: 'Previous audit page' }),
    ).toBeEnabled()
  })

  it('disables duplicate requests while loading', () => {
    vi.mocked(loadReportAudit).mockImplementation(
      () => new Promise<IncidentAuditHistory>(() => {}),
    )

    renderAudit()

    fireEvent.change(
      screen.getByLabelText('Report reference for audit'),
      {
        target: { value: auditEvent.report_id },
      },
    )

    fireEvent.click(
      screen.getByRole('button', { name: 'Load audit history' }),
    )

    expect(
      screen.getByRole('button', { name: 'Loading audit history…' }),
    ).toBeDisabled()

    expect(
      screen.getByLabelText('Report reference for audit'),
    ).toBeDisabled()

    expect(loadReportAudit).toHaveBeenCalledTimes(1)
  })

  it('aborts the request when the panel unmounts', () => {
    vi.mocked(loadReportAudit).mockImplementation(
      () => new Promise<IncidentAuditHistory>(() => {}),
    )

    const { unmount } = renderAudit()

    fireEvent.change(
      screen.getByLabelText('Report reference for audit'),
      {
        target: { value: auditEvent.report_id },
      },
    )

    fireEvent.click(
      screen.getByRole('button', { name: 'Load audit history' }),
    )

    const signal = vi.mocked(loadReportAudit).mock.calls[0][1]
    expect(signal.aborted).toBe(false)

    unmount()

    expect(signal.aborted).toBe(true)
  })
})
