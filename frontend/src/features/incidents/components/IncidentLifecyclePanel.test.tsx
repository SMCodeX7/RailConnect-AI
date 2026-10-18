import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '../../../shared/api/http'
import type { StaffSession } from '../../auth/types'
import {
  amendIncident,
  loadIncidentSnapshot,
  resolveIncident,
} from '../lifecycleApi'
import type { PublicIncidentSnapshot } from '../lifecycleTypes'
import { IncidentLifecyclePanel } from './IncidentLifecyclePanel'

vi.mock('../lifecycleApi', () => ({
  amendIncident: vi.fn(),
  loadIncidentSnapshot: vi.fn(),
  resolveIncident: vi.fn(),
}))

const session: StaffSession = {
  actor: {
    user_id: 'synthetic-controller-id',
    username: 'synthetic_controller',
    display_name: 'Synthetic Controller',
    roles: ['controller'],
    permissions: ['incidents.edit', 'incidents.resolve'],
  },
  csrf_token: 'current-lifecycle-csrf',
  expires_at: '2099-01-01T00:00:00Z',
}

const incident: PublicIncidentSnapshot = {
  incident_id: 'synthetic-incident-id',
  incident_version: 4,
  revision_id: 'synthetic-revision-2',
  revision_number: 2,
  status: 'active',
  run_id: 'synthetic-run-id',
  timetable_source_ref: 'synthetic-timetable-source',
  scope_kind: 'run',
  departure_stop_sequence: null,
  arrival_stop_sequence: null,
  impact_kind: 'delay',
  estimated_delay_minutes: 15,
  effective_from: '2020-01-02T05:00:00Z',
  effective_until: '2020-01-02T09:00:00Z',
  public_summary: 'Synthetic approved delay.',
  verified_at: '2020-01-02T04:00:00Z',
  resolution_effective_at: null,
}

function renderLifecycle(currentSession = session) {
  const onSessionInvalid = vi.fn()

  const view = render(
    <IncidentLifecyclePanel
      session={currentSession}
      onSessionInvalid={onSessionInvalid}
    />,
  )

  return { ...view, onSessionInvalid }
}

async function loadCurrentIncident() {
  const user = userEvent.setup()

  fireEvent.change(screen.getByLabelText('Incident reference'), {
    target: { value: incident.incident_id },
  })

  await user.click(
    screen.getByRole('button', { name: 'Load current incident' }),
  )

  await screen.findByRole('heading', {
    name: 'Current approved incident',
  })

  return user
}

function fillResolution() {
  fireEvent.change(screen.getByLabelText('Lifecycle reason'), {
    target: { value: 'Synthetic disruption has ended.' },
  })

  fireEvent.change(
    screen.getByLabelText(/Effective resolution — Sri Lanka time/),
    {
      target: { value: '2020-01-02T11:30' },
    },
  )
}

function fillAmendment() {
  fireEvent.change(screen.getByLabelText('Lifecycle action'), {
    target: { value: 'amend' },
  })

  fireEvent.change(screen.getByLabelText('Lifecycle reason'), {
    target: { value: 'Updated synthetic evidence was reviewed.' },
  })

  fireEvent.change(
    screen.getByLabelText('Replacement estimated delay in minutes'),
    {
      target: { value: '30' },
    },
  )

  fireEvent.change(
    screen.getByLabelText('New private evidence basis'),
    {
      target: { value: 'Fresh controlled demonstration evidence.' },
    },
  )

  fireEvent.click(
    screen.getByRole('checkbox', {
      name: /I independently reviewed the complete replacement facts/,
    }),
  )
}

describe('Incident lifecycle panel', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    vi.mocked(loadIncidentSnapshot).mockResolvedValue(incident)
  })

  it('loads the current approved incident only when requested', async () => {
    renderLifecycle()

    expect(loadIncidentSnapshot).not.toHaveBeenCalled()

    await loadCurrentIncident()

    expect(loadIncidentSnapshot).toHaveBeenCalledWith(
      incident.incident_id,
      expect.any(AbortSignal),
    )

    expect(
      screen.getByText('Synthetic approved delay.'),
    ).toBeInTheDocument()

    expect(screen.getByText('synthetic-run-id')).toBeInTheDocument()
    expect(screen.getByText('Incident version')).toBeInTheDocument()
    expect(screen.getByText('Approved revision')).toBeInTheDocument()
  })

  it('does not offer lifecycle changes for a resolved incident', async () => {
    vi.mocked(loadIncidentSnapshot).mockResolvedValue({
      ...incident,
      status: 'resolved',
      resolution_effective_at: '2020-01-02T06:00:00Z',
    })

    renderLifecycle()
    await loadCurrentIncident()

    expect(
      screen.getByText(
        'This incident is resolved. Further changes are unavailable.',
      ),
    ).toBeInTheDocument()

    expect(
      screen.queryByRole('button', { name: 'Confirm resolution' }),
    ).not.toBeInTheDocument()

    expect(
      screen.queryByRole('button', { name: 'Save approved amendment' }),
    ).not.toBeInTheDocument()
  })

  it('resolves with the loaded version and current CSRF token, then refreshes', async () => {
    vi.mocked(loadIncidentSnapshot)
      .mockResolvedValueOnce(incident)
      .mockResolvedValueOnce({
        ...incident,
        status: 'resolved',
        incident_version: 5,
        resolution_effective_at: '2020-01-02T06:00:00Z',
      })

    vi.mocked(resolveIncident).mockResolvedValue({
      incident_id: incident.incident_id,
      originating_report_id: 'synthetic-report-id',
      status: 'resolved',
      incident_version: 5,
      current_revision_number: 2,
      current_revision_id: incident.revision_id,
    })

    renderLifecycle()
    const user = await loadCurrentIncident()
    fillResolution()

    await user.click(
      screen.getByRole('button', { name: 'Confirm resolution' }),
    )

    expect(resolveIncident).toHaveBeenCalledWith(
      incident.incident_id,
      {
        expected_version: 4,
        reason: 'Synthetic disruption has ended.',
        resolution_effective_at: '2020-01-02T06:00:00.000Z',
      },
      session.csrf_token,
      expect.any(AbortSignal),
    )

    expect(
      await screen.findByText('Incident resolved. Recorded version: 5.'),
    ).toBeInTheDocument()

    expect(
      await screen.findByText(
        'This incident is resolved. Further changes are unavailable.',
      ),
    ).toBeInTheDocument()

    expect(loadIncidentSnapshot).toHaveBeenCalledTimes(2)
  })

  it('amends complete approved facts with a fresh evidence basis', async () => {
    vi.mocked(loadIncidentSnapshot)
      .mockResolvedValueOnce(incident)
      .mockResolvedValueOnce({
        ...incident,
        incident_version: 5,
        revision_number: 3,
        revision_id: 'synthetic-revision-3',
        estimated_delay_minutes: 30,
      })

    vi.mocked(amendIncident).mockResolvedValue({
      incident_id: incident.incident_id,
      originating_report_id: 'synthetic-report-id',
      status: 'active',
      incident_version: 5,
      current_revision_number: 3,
      current_revision_id: 'synthetic-revision-3',
    })

    renderLifecycle()
    const user = await loadCurrentIncident()
    fillAmendment()

    expect(
      screen.getByLabelText(
        /Replacement effective start — Sri Lanka time/,
      ),
    ).toHaveValue('2020-01-02T10:30')

    await user.click(
      screen.getByRole('button', { name: 'Save approved amendment' }),
    )

    expect(amendIncident).toHaveBeenCalledWith(
      incident.incident_id,
      {
        expected_version: 4,
        reason: 'Updated synthetic evidence was reviewed.',
        approved: {
          run_id: incident.run_id,
          scope_kind: 'run',
          departure_stop_sequence: null,
          arrival_stop_sequence: null,
          impact_kind: 'delay',
          estimated_delay_minutes: 30,
          effective_from: '2020-01-02T05:00:00.000Z',
          effective_until: '2020-01-02T09:00:00.000Z',
          public_summary: incident.public_summary,
          evidence_basis: 'Fresh controlled demonstration evidence.',
        },
      },
      session.csrf_token,
      expect.any(AbortSignal),
    )

    expect(
      await screen.findByText('Incident amended. Recorded version: 5.'),
    ).toBeInTheDocument()

    await waitFor(() => {
      expect(loadIncidentSnapshot).toHaveBeenCalledTimes(2)
    })
  })

  it('blocks another mutation after a version conflict until reloaded', async () => {
    vi.mocked(resolveIncident).mockRejectedValue(
      new ApiError('Conflict.', 409, 'CONFLICT', null, null),
    )

    renderLifecycle()
    const user = await loadCurrentIncident()
    fillResolution()

    await user.click(
      screen.getByRole('button', { name: 'Confirm resolution' }),
    )

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'The incident changed or was resolved.',
    )

    expect(
      screen.getByRole('button', { name: 'Confirm resolution' }),
    ).toBeDisabled()

    expect(resolveIncident).toHaveBeenCalledTimes(1)

    await user.click(
      screen.getByRole('button', { name: 'Load current incident' }),
    )

    expect(
      await screen.findByRole('button', { name: 'Confirm resolution' }),
    ).toBeEnabled()

    expect(resolveIncident).toHaveBeenCalledTimes(1)
  })

  it.each([
    {
      permission: 'incidents.edit' as const,
      available: 'Amend approved facts',
      unavailable: 'Resolve incident',
    },
    {
      permission: 'incidents.resolve' as const,
      available: 'Resolve incident',
      unavailable: 'Amend approved facts',
    },
  ])(
    'shows only permitted actions for $permission',
    async ({ permission, available, unavailable }) => {
      renderLifecycle({
        ...session,
        actor: {
          ...session.actor,
          permissions: [permission],
        },
      })

      await loadCurrentIncident()

      expect(
        screen.getByRole('option', { name: available }),
      ).toBeInTheDocument()

      expect(
        screen.queryByRole('option', { name: unavailable }),
      ).not.toBeInTheDocument()
    },
  )

  it('rejects resolution before the current revision starts', async () => {
    renderLifecycle()
    const user = await loadCurrentIncident()
    fillResolution()

    fireEvent.change(
      screen.getByLabelText(/Effective resolution — Sri Lanka time/),
      {
        target: { value: '2020-01-02T09:30' },
      },
    )

    await user.click(
      screen.getByRole('button', { name: 'Confirm resolution' }),
    )

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Resolution time must not be in the future or before the current revision starts.',
    )

    expect(resolveIncident).not.toHaveBeenCalled()
  })

  it('requests session restoration after a mutation returns 401', async () => {
    vi.mocked(resolveIncident).mockRejectedValue(
      new ApiError(
        'Authentication required.',
        401,
        'UNAUTHENTICATED',
        null,
        null,
      ),
    )

    const { onSessionInvalid } = renderLifecycle()
    const user = await loadCurrentIncident()
    fillResolution()

    await user.click(
      screen.getByRole('button', { name: 'Confirm resolution' }),
    )

    await waitFor(() => {
      expect(onSessionInvalid).toHaveBeenCalledTimes(1)
    })
  })

  it('disables duplicate mutations while saving', async () => {
    vi.mocked(resolveIncident).mockImplementation(
      () => new Promise(() => {}),
    )

    renderLifecycle()
    await loadCurrentIncident()
    fillResolution()

    const button = screen.getByRole('button', {
      name: 'Confirm resolution',
    })

    fireEvent.click(button)
    fireEvent.click(button)

    expect(resolveIncident).toHaveBeenCalledTimes(1)

    expect(
      screen.getByRole('button', {
        name: 'Saving lifecycle change…',
      }),
    ).toBeDisabled()

    expect(
      screen.getByRole('button', { name: 'Load current incident' }),
    ).toBeDisabled()
  })

  it('aborts an incident request when unmounted', () => {
    vi.mocked(loadIncidentSnapshot).mockImplementation(
      () => new Promise<PublicIncidentSnapshot>(() => {}),
    )

    const { unmount } = renderLifecycle()

    fireEvent.change(screen.getByLabelText('Incident reference'), {
      target: { value: incident.incident_id },
    })

    fireEvent.click(
      screen.getByRole('button', { name: 'Load current incident' }),
    )

    const signal = vi.mocked(loadIncidentSnapshot).mock.calls[0][1]

    expect(signal.aborted).toBe(false)

    unmount()

    expect(signal.aborted).toBe(true)
  })

  it('preserves confirmed success when the subsequent refresh fails', async () => {
    vi.mocked(loadIncidentSnapshot)
      .mockResolvedValueOnce(incident)
      .mockRejectedValueOnce(new Error('Refresh unavailable.'))

    vi.mocked(resolveIncident).mockResolvedValue({
      incident_id: incident.incident_id,
      originating_report_id: 'synthetic-report-id',
      status: 'resolved',
      incident_version: 5,
      current_revision_number: 2,
      current_revision_id: incident.revision_id,
    })

    renderLifecycle()
    const user = await loadCurrentIncident()
    fillResolution()

    await user.click(
      screen.getByRole('button', { name: 'Confirm resolution' }),
    )

    expect(
      await screen.findByText('Incident resolved. Recorded version: 5.'),
    ).toBeInTheDocument()

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Unable to load the incident.',
    )

    expect(resolveIncident).toHaveBeenCalledTimes(1)
  })

  it('allows retry after an incident-loading failure', async () => {
    vi.mocked(loadIncidentSnapshot)
      .mockRejectedValueOnce(new Error('Unavailable.'))
      .mockResolvedValueOnce(incident)

    renderLifecycle()
    const user = userEvent.setup()

    fireEvent.change(screen.getByLabelText('Incident reference'), {
      target: { value: incident.incident_id },
    })

    await user.click(
      screen.getByRole('button', { name: 'Load current incident' }),
    )

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Unable to load the incident.',
    )

    await user.click(
      screen.getByRole('button', { name: 'Load current incident' }),
    )

    expect(
      await screen.findByRole('heading', {
        name: 'Current approved incident',
      }),
    ).toBeInTheDocument()

    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('clears the loaded incident when its reference is edited', async () => {
    renderLifecycle()
    await loadCurrentIncident()

    fireEvent.change(screen.getByLabelText('Incident reference'), {
      target: { value: 'another-incident-reference' },
    })

    expect(
      screen.queryByRole('heading', {
        name: 'Current approved incident',
      }),
    ).not.toBeInTheDocument()

    expect(
      screen.queryByRole('button', { name: 'Confirm resolution' }),
    ).not.toBeInTheDocument()

    expect(loadIncidentSnapshot).toHaveBeenCalledTimes(1)
  })
})
