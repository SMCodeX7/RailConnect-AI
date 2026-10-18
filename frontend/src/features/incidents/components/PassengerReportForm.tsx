import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'

import { ApiError } from '../../../shared/api/http'
import { submitPassengerReport } from '../api'
import type { ReportSubmission } from '../types'

function reportErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 429) {
      return error.retryAfter !== null
        ? `Too many reports. Try again in ${error.retryAfter} seconds.`
        : 'Too many reports. Please try again later.'
    }

    if (error.status === 401) {
      return 'Your staff session is no longer valid. Open Staff access to sign in or clear the session, then try again.'
    }

    if (error.status === 403) {
      return 'Submission was denied. Refresh your staff session if signed in, and check the application address.'
    }

    if (error.status === 422) {
      return 'Check your report details. The observation time must not be in the future.'
    }
  }

  return 'Submission could not be confirmed. Your report may have been received. Avoid immediately submitting it again.'
}

function formatSubmittedAt(value: string): string {
  return new Intl.DateTimeFormat('en-GB', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: 'Asia/Colombo',
  }).format(new Date(value))
}

export function PassengerReportForm() {
  const controllerRef = useRef<AbortController | null>(null)
  const pendingRef = useRef(false)

  const [title, setTitle] = useState('')
  const [narrative, setNarrative] = useState('')
  const [observedAt, setObservedAt] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [receipt, setReceipt] = useState<ReportSubmission | null>(null)

  useEffect(() => {
    return () => {
      controllerRef.current?.abort()
    }
  }, [])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (pendingRef.current) return

    const cleanTitle = title.trim()
    const cleanNarrative = narrative.trim()

    if (!cleanTitle || !cleanNarrative || !observedAt) {
      setError('Enter a title, description and observation time.')
      return
    }

    const observation = new Date(`${observedAt}:00+05:30`)

    if (
      !Number.isFinite(observation.getTime()) ||
      observation.getTime() > Date.now()
    ) {
      setError(
        'Enter a valid observation time that is not in the future. Use Sri Lanka time.',
      )
      return
    }

    pendingRef.current = true
    controllerRef.current?.abort()

    const controller = new AbortController()
    controllerRef.current = controller

    setBusy(true)
    setError(null)

    try {
      const result = await submitPassengerReport(
        {
          title: cleanTitle,
          narrative: cleanNarrative,
          observed_at: observation.toISOString(),
        },
        controller.signal,
      )

      if (
        controller.signal.aborted ||
        controllerRef.current !== controller
      ) {
        return
      }

      setReceipt(result)
      setTitle('')
      setNarrative('')
      setObservedAt('')
    } catch (submissionError) {
      if (
        !controller.signal.aborted &&
        controllerRef.current === controller
      ) {
        setError(reportErrorMessage(submissionError))
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

  function startAnotherReport() {
    setReceipt(null)
    setError(null)
  }

  return (
    <section
      className="passenger-report-panel"
      aria-labelledby="passenger-report-heading"
      aria-busy={busy}
    >
      <h2 id="passenger-report-heading">Report a disruption</h2>

      <p>
        Reports are unverified claims until reviewed by authorized staff.
        Submitting a report does not change journey results.
      </p>

      <p className="muted">
        This portfolio pilot uses demonstration data. Do not include
        passwords, contact details or other private personal information.
      </p>

      {receipt ? (
        <div className="report-receipt">
          <p role="status">
            Report received. Its status is pending staff review.
          </p>

          <dl>
            <div>
              <dt>Report reference</dt>
              <dd>{receipt.report_id}</dd>
            </div>

            <div>
              <dt>Status</dt>
              <dd>Pending</dd>
            </div>

            <div>
              <dt>Submitted</dt>
              <dd>
                <time dateTime={receipt.submitted_at}>
                  {formatSubmittedAt(receipt.submitted_at)}
                </time>
                {' '}(Asia/Colombo)
              </dd>
            </div>
          </dl>

          <p>This receipt does not verify the reported disruption.</p>

          <button type="button" onClick={startAnotherReport}>
            Start another report
          </button>
        </div>
      ) : (
        <form onSubmit={(event) => void handleSubmit(event)}>
          <fieldset disabled={busy} className="report-fields">
            <legend>What did you observe?</legend>

            <div className="report-field">
              <label htmlFor="passenger-report-title">Report title</label>
              <input
                id="passenger-report-title"
                name="title"
                type="text"
                required
                maxLength={160}
                value={title}
                onChange={(event) => setTitle(event.target.value)}
              />
            </div>

            <div className="report-field">
              <label htmlFor="passenger-report-narrative">
                Describe what you observed
              </label>

              <textarea
                id="passenger-report-narrative"
                name="narrative"
                required
                maxLength={4000}
                rows={6}
                aria-describedby="passenger-report-description-help"
                value={narrative}
                onChange={(event) => setNarrative(event.target.value)}
              />

              <p
                id="passenger-report-description-help"
                className="muted"
              >
                Include the service, station or location if known.
                Describe observations without presenting guesses as facts.
                Maximum 4000 characters.
              </p>
            </div>

            <div className="report-field">
              <label htmlFor="passenger-report-observed-at">
                Observation date and time
              </label>

              <input
                id="passenger-report-observed-at"
                name="observed_at"
                type="datetime-local"
                required
                step={60}
                aria-describedby="passenger-report-time-help"
                value={observedAt}
                onChange={(event) => setObservedAt(event.target.value)}
              />

              <p id="passenger-report-time-help" className="muted">
                Enter Sri Lanka time (Asia/Colombo). Future observations
                are not accepted.
              </p>
            </div>

            <button type="submit">
              {busy ? 'Submitting report…' : 'Submit report'}
            </button>
          </fieldset>

          {busy && (
            <p role="status">Submitting your report. Please wait…</p>
          )}

          {error && (
            <p className="error" role="alert">
              {error}
            </p>
          )}
        </form>
      )}
    </section>
  )
}
