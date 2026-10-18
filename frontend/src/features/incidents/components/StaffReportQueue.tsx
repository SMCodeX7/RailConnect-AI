import { useEffect, useRef, useState } from 'react'

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
  RejectReportInput,
  ReportReviewResult,
  VerifyReportInput,
} from '../staffTypes'
import { ReportReviewForm } from './ReportReviewForm'

interface StaffReportQueueProps {
  session: StaffSession
  onSessionInvalid: () => void
}

function staffErrorMessage(error: unknown, mutation: boolean): string {
  if (error instanceof ApiError) {
    if (error.status === 403) {
      return 'Access was denied. Refresh your session to check current permissions.'
    }

    if (error.status === 409) {
      return 'This report changed or was already reviewed. Reload the queue before making another decision.'
    }

    if (error.status === 404) {
      return 'The report is no longer available. Reload the queue.'
    }

    if (error.status === 422) {
      return 'Check the approved facts, prepared run ID, stop sequences and effective times.'
    }
  }

  return mutation
    ? 'The decision could not be confirmed. Reload the queue before retrying.'
    : 'Unable to load passenger reports. Please try again.'
}

function displayTime(value: string): string {
  return new Intl.DateTimeFormat('en-GB', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: 'Asia/Colombo',
  }).format(new Date(value))
}

export function StaffReportQueue({
  session,
  onSessionInvalid,
}: StaffReportQueueProps) {
  const controllerRef = useRef<AbortController | null>(null)
  const pendingRef = useRef(false)

  const [queue, setQueue] = useState<PendingReportQueue | null>(null)
  const [selected, setSelected] = useState<PendingReport | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [needsReload, setNeedsReload] = useState(false)

  const canReview = session.actor.permissions.includes('reports.review')

  useEffect(() => {
    return () => controllerRef.current?.abort()
  }, [])

  function handleError(failure: unknown, mutation: boolean) {
    if (failure instanceof ApiError && failure.status === 401) {
      onSessionInvalid()
      return
    }

    setError(staffErrorMessage(failure, mutation))

    if (mutation) {
      setNeedsReload(true)
    }
  }

  async function loadPage(offset = 0) {
    if (pendingRef.current) return

    pendingRef.current = true
    controllerRef.current?.abort()

    const controller = new AbortController()
    controllerRef.current = controller

    setBusy(true)
    setError(null)
    setSelected(null)
    setQueue(null)
    setNeedsReload(true)

    try {
      const result = await loadPendingReports(controller.signal, offset)

      if (
        !controller.signal.aborted &&
        controllerRef.current === controller
      ) {
        setQueue(result)
        setNeedsReload(false)
      }
    } catch (failure) {
      if (
        !controller.signal.aborted &&
        controllerRef.current === controller
      ) {
        handleError(failure, false)
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

  async function decide(
    action: (
      report: PendingReport,
      signal: AbortSignal,
    ) => Promise<ReportReviewResult>,
  ) {
    if (!selected || !canReview || pendingRef.current || needsReload) return

    pendingRef.current = true
    controllerRef.current?.abort()

    const controller = new AbortController()
    controllerRef.current = controller

    setBusy(true)
    setError(null)
    setNotice(null)

    let succeeded = false

    try {
      const result = await action(selected, controller.signal)

      if (
        !controller.signal.aborted &&
        controllerRef.current === controller
      ) {
        setNotice(
          result.status === 'verified'
            ? `Report verified. Incident reference: ${result.incident_id}.`
            : 'Report rejected. The decision was recorded.',
        )
        setSelected(null)
        setQueue(null)
        setNeedsReload(true)
        succeeded = true
      }
    } catch (failure) {
      if (
        !controller.signal.aborted &&
        controllerRef.current === controller
      ) {
        handleError(failure, true)
      }
    } finally {
      if (controllerRef.current === controller) {
        pendingRef.current = false

        if (!controller.signal.aborted) {
          setBusy(false)
        }
      }
    }

    if (succeeded && !controller.signal.aborted) {
      await loadPage(0)
    }
  }

  async function verify(input: VerifyReportInput) {
    await decide((report, signal) =>
      verifyPassengerReport(
        report.report_id,
        input,
        session.csrf_token,
        signal,
      ),
    )
  }

  async function reject(input: RejectReportInput) {
    await decide((report, signal) =>
      rejectPassengerReport(
        report.report_id,
        input,
        session.csrf_token,
        signal,
      ),
    )
  }

  return (
    <section
      className="staff-report-queue"
      aria-labelledby="staff-report-queue-heading"
      aria-busy={busy}
    >
      <h3 id="staff-report-queue-heading">Passenger report queue</h3>

      <p className="muted">
        Pending reports are unverified claims. All times below are
        displayed in Asia/Colombo.
      </p>

      <button
        type="button"
        disabled={busy}
        onClick={() => void loadPage(0)}
      >
        {queue || needsReload ? 'Reload report queue' : 'Load pending reports'}
      </button>

      {busy && <p role="status">Working on the report queue…</p>}
      {notice && <p role="status">{notice}</p>}
      {error && <p className="error" role="alert">{error}</p>}

      {needsReload && !busy && (
        <p className="muted">
          Load the queue successfully before submitting another decision.
        </p>
      )}

      {queue && (
        <>
          <p>{queue.total} pending reports.</p>

          {queue.items.length === 0 ? (
            <p>No pending reports on this page.</p>
          ) : (
            <ol className="pending-report-list">
              {queue.items.map((report) => (
                <li key={report.report_id}>
                  <h4>{report.title}</h4>

                  <p className="report-narrative">{report.narrative}</p>

                  <dl>
                    <div>
                      <dt>Report reference</dt>
                      <dd>{report.report_id}</dd>
                    </div>
                    <div>
                      <dt>Observed</dt>
                      <dd>
                        <time dateTime={report.observed_at}>
                          {displayTime(report.observed_at)}
                        </time>
                      </dd>
                    </div>
                    <div>
                      <dt>Submitted</dt>
                      <dd>
                        <time dateTime={report.submitted_at}>
                          {displayTime(report.submitted_at)}
                        </time>
                      </dd>
                    </div>
                    <div>
                      <dt>Unverified run hint</dt>
                      <dd>{report.run_hint_id ?? 'Not provided'}</dd>
                    </div>
                    <div>
                      <dt>Unverified station hint</dt>
                      <dd>{report.station_hint_id ?? 'Not provided'}</dd>
                    </div>
                    <div>
                      <dt>Unverified segment hint</dt>
                      <dd>
                        {report.departure_stop_sequence_hint !== null &&
                        report.arrival_stop_sequence_hint !== null
                          ? `${report.departure_stop_sequence_hint} to ${report.arrival_stop_sequence_hint}`
                          : 'Not provided'}
                      </dd>
                    </div>
                  </dl>

                  <button
                    type="button"
                    disabled={busy || needsReload}
                    onClick={() => {
                      setSelected(report)
                      setError(null)
                    }}
                  >
                    Open report review
                  </button>
                </li>
              ))}
            </ol>
          )}

          <div className="staff-actions">
            <button
              type="button"
              disabled={busy || queue.offset === 0}
              onClick={() =>
                void loadPage(Math.max(0, queue.offset - queue.limit))
              }
            >
              Previous report page
            </button>

            <button
              type="button"
              disabled={
                busy ||
                queue.offset + queue.limit >= queue.total ||
                queue.offset + queue.limit > 10000
              }
              onClick={() =>
                void loadPage(queue.offset + queue.limit)
              }
            >
              Next report page
            </button>
          </div>
        </>
      )}

      {selected && (
        <ReportReviewForm
          key={selected.report_id}
          report={selected}
          busy={busy}
          blocked={needsReload}
          canReview={canReview}
          onVerify={verify}
          onReject={reject}
          onCancel={() => setSelected(null)}
        />
      )}
    </section>
  )
}
