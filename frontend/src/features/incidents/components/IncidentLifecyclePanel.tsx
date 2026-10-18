import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'

import { ApiError } from '../../../shared/api/http'
import type { StaffSession } from '../../auth/types'
import {
  amendIncident,
  loadIncidentSnapshot,
  resolveIncident,
} from '../lifecycleApi'
import type {
  IncidentLifecycleResult,
  PublicIncidentSnapshot,
} from '../lifecycleTypes'

interface IncidentLifecyclePanelProps {
  session: StaffSession
  onSessionInvalid: () => void
}

function localInputValue(timestamp: string): string {
  const milliseconds = Date.parse(timestamp)

  if (!Number.isFinite(milliseconds)) return ''

  return new Date(milliseconds + 330 * 60 * 1000)
    .toISOString()
    .slice(0, 16)
}

function toUtc(value: string): string | null {
  if (!value) return null

  const date = new Date(`${value}:00+05:30`)

  return Number.isFinite(date.getTime()) ? date.toISOString() : null
}

function displayTime(timestamp: string): string {
  return new Intl.DateTimeFormat('en-GB', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: 'Asia/Colombo',
  }).format(new Date(timestamp))
}

function lifecycleErrorMessage(error: unknown, mutation: boolean): string {
  if (error instanceof ApiError) {
    if (error.status === 403) {
      return 'Permission was denied. Refresh your staff session.'
    }

    if (error.status === 404) {
      return 'The incident was not found.'
    }

    if (error.status === 409) {
      return 'The incident changed or was resolved. Reload it before another decision.'
    }

    if (error.status === 422) {
      return 'Check the incident reference, approved scope, impact and effective times.'
    }

    if (error.status === 503) {
      return 'The incident history is temporarily unavailable.'
    }
  }

  return mutation
    ? 'The change could not be confirmed. Reload the incident before retrying.'
    : 'Unable to load the incident. Please try again.'
}

export function IncidentLifecyclePanel({
  session,
  onSessionInvalid,
}: IncidentLifecyclePanelProps) {
  const controllerRef = useRef<AbortController | null>(null)
  const pendingRef = useRef(false)

  const [reference, setReference] = useState('')
  const [incident, setIncident] = useState<PublicIncidentSnapshot | null>(null)
  const [action, setAction] = useState<'amend' | 'resolve'>('resolve')
  const [scope, setScope] = useState<'run' | 'segment'>('run')
  const [impact, setImpact] = useState<
    'cancellation' | 'restriction' | 'delay'
  >('restriction')
  const [busy, setBusy] = useState(false)
  const [needsReload, setNeedsReload] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)

  const canAmend = session.actor.permissions.includes('incidents.edit')
  const canResolve = session.actor.permissions.includes('incidents.resolve')
  const canPerformAction = action === 'amend' ? canAmend : canResolve

  useEffect(() => {
    return () => controllerRef.current?.abort()
  }, [])

  function reportFailure(failure: unknown, mutation: boolean) {
    if (failure instanceof ApiError && failure.status === 401) {
      onSessionInvalid()
      return
    }

    setError(lifecycleErrorMessage(failure, mutation))
  }

  async function loadIncident(incidentId: string) {
    if (pendingRef.current) return

    const cleanReference = incidentId.trim()

    if (!cleanReference) {
      setError('Enter an incident reference.')
      return
    }

    pendingRef.current = true
    controllerRef.current?.abort()

    const controller = new AbortController()
    controllerRef.current = controller

    setBusy(true)
    setError(null)
    setIncident(null)
    setNeedsReload(true)

    try {
      const result = await loadIncidentSnapshot(
        cleanReference,
        controller.signal,
      )

      if (
        !controller.signal.aborted &&
        controllerRef.current === controller
      ) {
        setIncident(result)
        setScope(result.scope_kind)
        setImpact(result.impact_kind)
        setAction(canResolve ? 'resolve' : 'amend')
        setNeedsReload(false)
      }
    } catch (failure) {
      if (
        !controller.signal.aborted &&
        controllerRef.current === controller
      ) {
        reportFailure(failure, false)
      }
    } finally {
      if (controllerRef.current === controller) {
        pendingRef.current = false

        if (!controller.signal.aborted) {
          setBusy(false)
        }
      }
    }
  }

  async function handleChange(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (
      !incident ||
      incident.status !== 'active' ||
      !canPerformAction ||
      pendingRef.current ||
      needsReload
    ) {
      return
    }

    const form = new FormData(event.currentTarget)
    const text = (name: string) => String(form.get(name) ?? '').trim()
    const reason = text('reason')

    setError(null)

    if (!reason) {
      setError('Enter a reason for the lifecycle change.')
      return
    }

    let operation: (
      signal: AbortSignal,
    ) => Promise<IncidentLifecycleResult>

    if (action === 'resolve') {
      const effective = toUtc(text('resolution_effective_at'))

      if (
        !effective ||
        Date.parse(effective) > Date.now() ||
        Date.parse(effective) < Date.parse(incident.effective_from)
      ) {
        setError(
          'Resolution time must not be in the future or before the current revision starts.',
        )
        return
      }

      operation = (signal) =>
        resolveIncident(
          incident.incident_id,
          {
            expected_version: incident.incident_version,
            reason,
            resolution_effective_at: effective,
          },
          session.csrf_token,
          signal,
        )
    } else {
      const start = toUtc(text('effective_from'))
      const end = toUtc(text('effective_until'))

      if (!start || !end || Date.parse(end) <= Date.parse(start)) {
        setError('The effective end must follow the effective start.')
        return
      }

      const departure = scope === 'segment' ? Number(text('departure')) : null
      const arrival = scope === 'segment' ? Number(text('arrival')) : null

      if (
        scope === 'segment' &&
        (
          departure === null ||
          arrival === null ||
          !Number.isInteger(departure) ||
          !Number.isInteger(arrival) ||
          departure < 1 ||
          arrival <= departure
        )
      ) {
        setError('Enter positive, ordered segment stop sequences.')
        return
      }

      if (impact === 'cancellation' && scope !== 'run') {
        setError('Cancellation requires whole-run scope.')
        return
      }

      const delay = impact === 'delay' ? Number(text('delay')) : null

      if (
        impact === 'delay' &&
        (
          delay === null ||
          !Number.isInteger(delay) ||
          delay < 1 ||
          delay > 1440
        )
      ) {
        setError('Enter an estimated delay from 1 to 1440 minutes.')
        return
      }

      const runId = text('run_id')
      const summary = text('public_summary')
      const basis = text('evidence_basis')

      if (!runId || !summary || !basis || form.get('confirmed') !== 'on') {
        setError('Complete and independently confirm the approved facts.')
        return
      }

      operation = (signal) =>
        amendIncident(
          incident.incident_id,
          {
            expected_version: incident.incident_version,
            reason,
            approved: {
              run_id: runId,
              scope_kind: scope,
              departure_stop_sequence: departure,
              arrival_stop_sequence: arrival,
              impact_kind: impact,
              estimated_delay_minutes: delay,
              effective_from: start,
              effective_until: end,
              public_summary: summary,
              evidence_basis: basis,
            },
          },
          session.csrf_token,
          signal,
        )
    }

    pendingRef.current = true
    controllerRef.current?.abort()

    const controller = new AbortController()
    controllerRef.current = controller

    setBusy(true)
    setNotice(null)

    let confirmedIncidentId: string | null = null

    try {
      const result = await operation(controller.signal)

      if (
        !controller.signal.aborted &&
        controllerRef.current === controller
      ) {
        setNotice(
          `Incident ${result.status === 'resolved' ? 'resolved' : 'amended'}. Recorded version: ${result.incident_version}.`,
        )
        setNeedsReload(true)
        confirmedIncidentId = result.incident_id
      }
    } catch (failure) {
      if (
        !controller.signal.aborted &&
        controllerRef.current === controller
      ) {
        setNeedsReload(true)
        reportFailure(failure, true)
      }
    } finally {
      if (controllerRef.current === controller) {
        pendingRef.current = false

        if (!controller.signal.aborted) {
          setBusy(false)
        }
      }
    }

    if (confirmedIncidentId && !controller.signal.aborted) {
      await loadIncident(confirmedIncidentId)
    }
  }

  return (
    <section
      className="incident-lifecycle-panel"
      aria-labelledby="incident-lifecycle-heading"
      aria-busy={busy}
    >
      <h3 id="incident-lifecycle-heading">Manage a verified incident</h3>

      <p className="muted">
        Load the current approved revision before making a change.
        Times are entered and displayed in Asia/Colombo.
      </p>

      <form
        onSubmit={(event) => {
          event.preventDefault()
          setNotice(null)
          void loadIncident(reference)
        }}
      >
        <fieldset disabled={busy} className="report-fields">
          <legend>Find incident</legend>

          <div className="report-field">
            <label htmlFor="lifecycle-reference">Incident reference</label>
            <input
              id="lifecycle-reference"
              required
              value={reference}
              onChange={(event) => {
                setReference(event.target.value)
                setIncident(null)
                setNotice(null)
                setError(null)
              }}
            />
          </div>

          <button type="submit">Load current incident</button>
        </fieldset>
      </form>

      {busy && <p role="status">Working on the incident…</p>}
      {notice && <p role="status">{notice}</p>}
      {error && <p className="error" role="alert">{error}</p>}

      {needsReload && incident && !busy && (
        <p>Reload the incident before making another change.</p>
      )}

      {incident && (
        <>
          <h4>Current approved incident</h4>

          <dl className="staff-account-details">
            <div>
              <dt>Status</dt>
              <dd>{incident.status}</dd>
            </div>
            <div>
              <dt>Incident version</dt>
              <dd>{incident.incident_version}</dd>
            </div>
            <div>
              <dt>Approved revision</dt>
              <dd>{incident.revision_number}</dd>
            </div>
            <div>
              <dt>Public summary</dt>
              <dd>{incident.public_summary}</dd>
            </div>
            <div>
              <dt>Approved run reference</dt>
              <dd>{incident.run_id}</dd>
            </div>
            <div>
              <dt>Effective start</dt>
              <dd>{displayTime(incident.effective_from)}</dd>
            </div>
            <div>
              <dt>Effective end</dt>
              <dd>{displayTime(incident.effective_until)}</dd>
            </div>
            {incident.resolution_effective_at && (
              <div>
                <dt>Effective resolution</dt>
                <dd>{displayTime(incident.resolution_effective_at)}</dd>
              </div>
            )}
          </dl>

          {incident.status === 'resolved' ? (
            <p>This incident is resolved. Further changes are unavailable.</p>
          ) : (
            <form
              key={`${incident.incident_id}:${incident.incident_version}:${action}`}
              onSubmit={(event) => void handleChange(event)}
            >
              <fieldset
                disabled={busy || needsReload}
                className="report-fields"
              >
                <legend>Versioned lifecycle change</legend>

                <div className="report-field">
                  <label htmlFor="lifecycle-action">Lifecycle action</label>
                  <select
                    id="lifecycle-action"
                    value={action}
                    onChange={(event) => {
                      setAction(event.target.value as 'amend' | 'resolve')
                      setError(null)
                    }}
                  >
                    {canResolve && <option value="resolve">Resolve incident</option>}
                    {canAmend && <option value="amend">Amend approved facts</option>}
                  </select>
                </div>

                <div className="report-field">
                  <label htmlFor="lifecycle-reason">Lifecycle reason</label>
                  <textarea
                    id="lifecycle-reason"
                    name="reason"
                    required
                    maxLength={2000}
                    rows={3}
                  />
                </div>

                {action === 'resolve' ? (
                  <div className="report-field">
                    <label htmlFor="lifecycle-resolution-time">
                      Effective resolution — Sri Lanka time
                    </label>
                    <input
                      id="lifecycle-resolution-time"
                      name="resolution_effective_at"
                      type="datetime-local"
                      required
                      step={60}
                    />
                  </div>
                ) : (
                  <>
                    <p className="muted">
                      Existing approved fields are prefilled. Enter a fresh
                      evidence basis and confirm the complete replacement facts.
                    </p>

                    <div className="report-field">
                      <label htmlFor="lifecycle-run">Replacement approved run ID</label>
                      <input
                        id="lifecycle-run"
                        name="run_id"
                        required
                        defaultValue={incident.run_id}
                      />
                    </div>

                    <div className="report-field">
                      <label htmlFor="lifecycle-scope">Replacement scope</label>
                      <select
                        id="lifecycle-scope"
                        value={scope}
                        onChange={(event) =>
                          setScope(event.target.value as 'run' | 'segment')
                        }
                      >
                        <option value="run">Whole dated run</option>
                        <option value="segment">Ordered stop segment</option>
                      </select>
                    </div>

                    {scope === 'segment' && (
                      <>
                        <div className="report-field">
                          <label htmlFor="lifecycle-departure">
                            Replacement departure sequence
                          </label>
                          <input
                            id="lifecycle-departure"
                            name="departure"
                            type="number"
                            min={1}
                            step={1}
                            required
                            defaultValue={incident.departure_stop_sequence ?? ''}
                          />
                        </div>

                        <div className="report-field">
                          <label htmlFor="lifecycle-arrival">
                            Replacement arrival sequence
                          </label>
                          <input
                            id="lifecycle-arrival"
                            name="arrival"
                            type="number"
                            min={2}
                            step={1}
                            required
                            defaultValue={incident.arrival_stop_sequence ?? ''}
                          />
                        </div>
                      </>
                    )}

                    <div className="report-field">
                      <label htmlFor="lifecycle-impact">Replacement impact</label>
                      <select
                        id="lifecycle-impact"
                        value={impact}
                        onChange={(event) =>
                          setImpact(
                            event.target.value as
                              | 'cancellation'
                              | 'restriction'
                              | 'delay',
                          )
                        }
                      >
                        <option value="restriction">Restriction</option>
                        <option value="delay">Estimated delay</option>
                        <option value="cancellation">Cancellation</option>
                      </select>
                    </div>

                    {impact === 'delay' && (
                      <div className="report-field">
                        <label htmlFor="lifecycle-delay">
                          Replacement estimated delay in minutes
                        </label>
                        <input
                          id="lifecycle-delay"
                          name="delay"
                          type="number"
                          min={1}
                          max={1440}
                          step={1}
                          required
                          defaultValue={incident.estimated_delay_minutes ?? ''}
                        />
                      </div>
                    )}

                    <div className="report-field">
                      <label htmlFor="lifecycle-start">
                        Replacement effective start — Sri Lanka time
                      </label>
                      <input
                        id="lifecycle-start"
                        name="effective_from"
                        type="datetime-local"
                        required
                        step={60}
                        defaultValue={localInputValue(incident.effective_from)}
                      />
                    </div>

                    <div className="report-field">
                      <label htmlFor="lifecycle-end">
                        Replacement effective end — Sri Lanka time
                      </label>
                      <input
                        id="lifecycle-end"
                        name="effective_until"
                        type="datetime-local"
                        required
                        step={60}
                        defaultValue={localInputValue(incident.effective_until)}
                      />
                    </div>

                    <div className="report-field">
                      <label htmlFor="lifecycle-summary">
                        Replacement public summary
                      </label>
                      <textarea
                        id="lifecycle-summary"
                        name="public_summary"
                        required
                        maxLength={1000}
                        rows={3}
                        defaultValue={incident.public_summary}
                      />
                    </div>

                    <div className="report-field">
                      <label htmlFor="lifecycle-basis">New private evidence basis</label>
                      <textarea
                        id="lifecycle-basis"
                        name="evidence_basis"
                        required
                        maxLength={2000}
                        rows={3}
                      />
                    </div>

                    <label className="review-confirmation">
                      <input type="checkbox" name="confirmed" required />
                      I independently reviewed the complete replacement facts.
                    </label>
                  </>
                )}

                <button type="submit" disabled={!canPerformAction}>
                  {busy
                    ? 'Saving lifecycle change…'
                    : action === 'amend'
                      ? 'Save approved amendment'
                      : 'Confirm resolution'}
                </button>
              </fieldset>
            </form>
          )}
        </>
      )}
    </section>
  )
}
