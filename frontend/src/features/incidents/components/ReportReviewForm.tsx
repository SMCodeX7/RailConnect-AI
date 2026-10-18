import { useState } from 'react'
import type { FormEvent } from 'react'

import type {
  PendingReport,
  RejectReportInput,
  VerifyReportInput,
} from '../staffTypes'

interface ReportReviewFormProps {
  report: PendingReport
  busy: boolean
  blocked: boolean
  canReview: boolean
  onVerify: (input: VerifyReportInput) => Promise<void>
  onReject: (input: RejectReportInput) => Promise<void>
  onCancel: () => void
}

function sriLankaTimestamp(value: string): string | null {
  if (!value) return null

  const date = new Date(`${value}:00+05:30`)
  return Number.isFinite(date.getTime()) ? date.toISOString() : null
}

export function ReportReviewForm({
  report,
  busy,
  blocked,
  canReview,
  onVerify,
  onReject,
  onCancel,
}: ReportReviewFormProps) {
  const [decision, setDecision] = useState<'verify' | 'reject'>('reject')
  const [reason, setReason] = useState('')
  const [runId, setRunId] = useState(report.run_hint_id ?? '')
  const [scope, setScope] = useState<'run' | 'segment'>('run')
  const [departure, setDeparture] = useState('')
  const [arrival, setArrival] = useState('')
  const [impact, setImpact] = useState<
    'cancellation' | 'restriction' | 'delay'
  >('restriction')
  const [delay, setDelay] = useState('')
  const [effectiveFrom, setEffectiveFrom] = useState('')
  const [effectiveUntil, setEffectiveUntil] = useState('')
  const [summary, setSummary] = useState('')
  const [basis, setBasis] = useState('')
  const [confirmed, setConfirmed] = useState(false)
  const [validationError, setValidationError] = useState<string | null>(null)

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()

    if (busy || blocked || !canReview) return

    setValidationError(null)

    if (!reason.trim()) {
      setValidationError('Enter a reason for the review decision.')
      return
    }

    if (decision === 'reject') {
      await onReject({
        expected_version: report.version,
        reason: reason.trim(),
      })
      return
    }

    const start = sriLankaTimestamp(effectiveFrom)
    const end = sriLankaTimestamp(effectiveUntil)

    if (!start || !end || Date.parse(end) <= Date.parse(start)) {
      setValidationError(
        'Enter valid effective times in Sri Lanka time. The end must follow the start.',
      )
      return
    }

    const departureSequence = scope === 'segment' ? Number(departure) : null
    const arrivalSequence = scope === 'segment' ? Number(arrival) : null

    if (
      scope === 'segment' &&
      (
        !Number.isInteger(departureSequence) ||
        !Number.isInteger(arrivalSequence) ||
        departureSequence === null ||
        arrivalSequence === null ||
        departureSequence < 1 ||
        arrivalSequence <= departureSequence
      )
    ) {
      setValidationError('Enter positive, ordered segment stop sequences.')
      return
    }

    if (impact === 'cancellation' && scope !== 'run') {
      setValidationError('Cancellation requires whole-run scope.')
      return
    }

    const delayMinutes = impact === 'delay' ? Number(delay) : null

    if (
      impact === 'delay' &&
      (
        delayMinutes === null ||
        !Number.isInteger(delayMinutes) ||
        delayMinutes < 1 ||
        delayMinutes > 1440
      )
    ) {
      setValidationError('Enter an estimated delay from 1 to 1440 minutes.')
      return
    }

    if (!runId.trim() || !summary.trim() || !basis.trim() || !confirmed) {
      setValidationError(
        'Complete the approved facts and confirm that you reviewed them independently.',
      )
      return
    }

    await onVerify({
      expected_version: report.version,
      reason: reason.trim(),
      approved: {
        run_id: runId.trim(),
        scope_kind: scope,
        departure_stop_sequence: departureSequence,
        arrival_stop_sequence: arrivalSequence,
        impact_kind: impact,
        estimated_delay_minutes: delayMinutes,
        effective_from: start,
        effective_until: end,
        public_summary: summary.trim(),
        evidence_basis: basis.trim(),
      },
    })
  }

  return (
    <section aria-labelledby="report-review-heading">
      <h4 id="report-review-heading">Review selected report</h4>

      <p>
        Report reference: {report.report_id}. Expected version: {report.version}.
      </p>

      <p className="demo-notice">
        Passenger narrative and scope hints are unverified. Approve facts
        independently before verification.
      </p>

      {!canReview && (
        <p>You have permission to read reports, but not to decide them.</p>
      )}

      <form onSubmit={(event) => void handleSubmit(event)}>
        <fieldset disabled={busy || blocked || !canReview} className="report-fields">
          <legend>Review decision</legend>

          <div className="report-field">
            <label htmlFor="review-decision">Decision</label>
            <select
              id="review-decision"
              value={decision}
              onChange={(event) =>
                setDecision(event.target.value as 'verify' | 'reject')
              }
            >
              <option value="reject">Reject report</option>
              <option value="verify">Verify approved incident</option>
            </select>
          </div>

          <div className="report-field">
            <label htmlFor="review-reason">Decision reason</label>
            <textarea
              id="review-reason"
              required
              maxLength={2000}
              rows={3}
              value={reason}
              onChange={(event) => setReason(event.target.value)}
            />
          </div>

          {decision === 'verify' && (
            <>
              <div className="report-field">
                <label htmlFor="review-run">Approved dated run ID</label>
                <input
                  id="review-run"
                  type="text"
                  required
                  value={runId}
                  onChange={(event) => setRunId(event.target.value)}
                  aria-describedby="review-run-help"
                />
                <p id="review-run-help" className="muted">
                  Use a prepared dated run UUID. Any prefilled value is
                  only the passenger’s unverified hint.
                </p>
              </div>

              <div className="report-field">
                <label htmlFor="review-scope">Approved scope</label>
                <select
                  id="review-scope"
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
                    <label htmlFor="review-departure">
                      Departure stop sequence
                    </label>
                    <input
                      id="review-departure"
                      type="number"
                      required
                      min={1}
                      step={1}
                      value={departure}
                      onChange={(event) => setDeparture(event.target.value)}
                    />
                  </div>

                  <div className="report-field">
                    <label htmlFor="review-arrival">
                      Arrival stop sequence
                    </label>
                    <input
                      id="review-arrival"
                      type="number"
                      required
                      min={2}
                      step={1}
                      value={arrival}
                      onChange={(event) => setArrival(event.target.value)}
                    />
                  </div>
                </>
              )}

              <div className="report-field">
                <label htmlFor="review-impact">Approved impact</label>
                <select
                  id="review-impact"
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
                  <label htmlFor="review-delay">
                    Approved estimated delay in minutes
                  </label>
                  <input
                    id="review-delay"
                    type="number"
                    required
                    min={1}
                    max={1440}
                    step={1}
                    value={delay}
                    onChange={(event) => setDelay(event.target.value)}
                  />
                </div>
              )}

              <div className="report-field">
                <label htmlFor="review-effective-from">
                  Effective start — Sri Lanka time
                </label>
                <input
                  id="review-effective-from"
                  type="datetime-local"
                  required
                  step={60}
                  value={effectiveFrom}
                  onChange={(event) => setEffectiveFrom(event.target.value)}
                />
              </div>

              <div className="report-field">
                <label htmlFor="review-effective-until">
                  Effective end — Sri Lanka time
                </label>
                <input
                  id="review-effective-until"
                  type="datetime-local"
                  required
                  step={60}
                  value={effectiveUntil}
                  onChange={(event) => setEffectiveUntil(event.target.value)}
                />
              </div>

              <div className="report-field">
                <label htmlFor="review-summary">Approved public summary</label>
                <textarea
                  id="review-summary"
                  required
                  maxLength={1000}
                  rows={3}
                  value={summary}
                  onChange={(event) => setSummary(event.target.value)}
                />
              </div>

              <div className="report-field">
                <label htmlFor="review-basis">Private evidence basis</label>
                <textarea
                  id="review-basis"
                  required
                  maxLength={2000}
                  rows={3}
                  value={basis}
                  onChange={(event) => setBasis(event.target.value)}
                />
              </div>

              <label className="review-confirmation">
                <input
                  type="checkbox"
                  required
                  checked={confirmed}
                  onChange={(event) => setConfirmed(event.target.checked)}
                />
                I independently reviewed the approved scope, impact,
                effective period and evidence basis.
              </label>
            </>
          )}

          <button type="submit">
            {busy
              ? 'Saving decision…'
              : decision === 'verify'
                ? 'Verify report'
                : 'Reject report'}
          </button>
        </fieldset>

        {validationError && (
          <p className="error" role="alert">
            {validationError}
          </p>
        )}
      </form>

      <button type="button" disabled={busy} onClick={onCancel}>
        Close review
      </button>
    </section>
  )
}
