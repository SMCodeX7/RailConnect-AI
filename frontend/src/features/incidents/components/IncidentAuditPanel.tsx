import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'

import { ApiError } from '../../../shared/api/http'
import { loadReportAudit } from '../lifecycleApi'
import type {
  IncidentAuditEvent,
  IncidentAuditHistory,
} from '../lifecycleTypes'

interface IncidentAuditPanelProps {
  onSessionInvalid: () => void
}

const actionLabels: Record<IncidentAuditEvent['action'], string> = {
  report_verified: 'Report verified',
  report_rejected: 'Report rejected',
  incident_revised: 'Incident amended',
  incident_resolved: 'Incident resolved',
}

function displayTime(value: string): string {
  return new Intl.DateTimeFormat('en-GB', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: 'Asia/Colombo',
  }).format(new Date(value))
}

function auditErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 403) {
      return 'Audit access was denied. Refresh your session to check current permissions.'
    }

    if (error.status === 404) {
      return 'No report exists with that reference.'
    }

    if (error.status === 422) {
      return 'Enter a valid report UUID.'
    }
  }

  return 'Unable to load audit history. Please try again.'
}

export function IncidentAuditPanel({
  onSessionInvalid,
}: IncidentAuditPanelProps) {
  const controllerRef = useRef<AbortController | null>(null)
  const pendingRef = useRef(false)

  const [reportId, setReportId] = useState('')
  const [history, setHistory] = useState<IncidentAuditHistory | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    return () => controllerRef.current?.abort()
  }, [])

  async function loadHistory(reference: string, offset = 0) {
    if (pendingRef.current) return

    const cleanReference = reference.trim()

    if (!cleanReference) {
      setError('Enter a report reference.')
      return
    }

    pendingRef.current = true
    controllerRef.current?.abort()

    const controller = new AbortController()
    controllerRef.current = controller

    setBusy(true)
    setError(null)
    setHistory(null)

    try {
      const result = await loadReportAudit(
        cleanReference,
        controller.signal,
        offset,
      )

      if (
        !controller.signal.aborted &&
        controllerRef.current === controller
      ) {
        setHistory(result)
      }
    } catch (failure) {
      if (
        !controller.signal.aborted &&
        controllerRef.current === controller
      ) {
        if (failure instanceof ApiError && failure.status === 401) {
          onSessionInvalid()
        } else {
          setError(auditErrorMessage(failure))
        }
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

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    void loadHistory(reportId)
  }

  return (
    <section
      className="incident-audit-panel"
      aria-labelledby="incident-audit-heading"
      aria-busy={busy}
    >
      <h3 id="incident-audit-heading">Private report audit history</h3>

      <p className="muted">
        Authorized staff only. History includes review decisions,
        amendments and resolution. Times are shown in Asia/Colombo.
      </p>

      <form onSubmit={handleSubmit}>
        <fieldset disabled={busy} className="report-fields">
          <legend>Find report history</legend>

          <div className="report-field">
            <label htmlFor="audit-report-reference">
              Report reference for audit
            </label>

            <input
              id="audit-report-reference"
              type="text"
              required
              value={reportId}
              onChange={(event) => {
                controllerRef.current?.abort()
                setReportId(event.target.value)
                setHistory(null)
                setError(null)
              }}
              aria-describedby="audit-reference-help"
            />

            <p id="audit-reference-help" className="muted">
              Use the report UUID from its submission receipt or staff
              review record. An incident UUID is a different reference.
            </p>
          </div>

          <button type="submit">
            {busy ? 'Loading audit history…' : 'Load audit history'}
          </button>
        </fieldset>
      </form>

      {busy && <p role="status">Loading private audit history…</p>}
      {error && <p className="error" role="alert">{error}</p>}

      {history && (
        <>
          <p role="status">
            {history.total} audit events for report {history.report_id}.
          </p>

          <p className="muted">
            Events are ordered by recorded time and event reference.
            Use versions to interpret changes recorded at the same time.
          </p>

          {history.items.length === 0 ? (
            <p>No audit events on this page.</p>
          ) : (
            <ol className="incident-audit-list">
              {history.items.map((event) => (
                <li key={event.event_id}>
                  <h4>{actionLabels[event.action] ?? event.action}</h4>

                  <p className="report-narrative">{event.reason}</p>

                  <dl>
                    <div>
                      <dt>Recorded</dt>
                      <dd>
                        <time dateTime={event.occurred_at}>
                          {displayTime(event.occurred_at)}
                        </time>
                      </dd>
                    </div>

                    <div>
                      <dt>Staff actor reference</dt>
                      <dd>{event.actor_id}</dd>
                    </div>

                    <div>
                      <dt>Report version</dt>
                      <dd>{event.report_version}</dd>
                    </div>

                    <div>
                      <dt>Incident reference</dt>
                      <dd>{event.incident_id ?? 'Not applicable'}</dd>
                    </div>

                    <div>
                      <dt>Incident version</dt>
                      <dd>{event.incident_version ?? 'Not applicable'}</dd>
                    </div>

                    <div>
                      <dt>Revision reference</dt>
                      <dd>{event.revision_id ?? 'Not applicable'}</dd>
                    </div>

                    <div>
                      <dt>Request reference</dt>
                      <dd>{event.request_id}</dd>
                    </div>

                    <div>
                      <dt>Audit event reference</dt>
                      <dd>{event.event_id}</dd>
                    </div>
                  </dl>
                </li>
              ))}
            </ol>
          )}

          <div className="staff-actions">
            <button
              type="button"
              disabled={busy || history.offset === 0}
              onClick={() =>
                void loadHistory(
                  history.report_id,
                  Math.max(0, history.offset - history.limit),
                )
              }
            >
              Previous audit page
            </button>

            <button
              type="button"
              disabled={
                busy ||
                history.offset + history.limit >= history.total ||
                history.offset + history.limit > 10000
              }
              onClick={() =>
                void loadHistory(
                  history.report_id,
                  history.offset + history.limit,
                )
              }
            >
              Next audit page
            </button>
          </div>
        </>
      )}
    </section>
  )
}
