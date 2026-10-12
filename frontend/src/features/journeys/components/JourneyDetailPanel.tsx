import { useEffect, useRef } from 'react'

import { formatDuration, formatJourneyTimestamp } from '../formatting'
import type { JourneyDetailState } from '../hooks/useJourneyDetail'

interface JourneyDetailPanelProps {
  state: JourneyDetailState
  onRetry: () => void
  onClose: () => void
}

export function JourneyDetailPanel({
  state,
  onRetry,
  onClose,
}: JourneyDetailPanelProps) {
  const headingRef = useRef<HTMLHeadingElement>(null)

  useEffect(() => {
    headingRef.current?.focus()
  }, [])

  const detail = state.result
  const segment = detail?.selected_segment

  return (
    <section
      className="journey-detail-panel"
      aria-labelledby="journey-detail-heading"
      aria-busy={state.status === 'loading'}
    >
      <div className="detail-header">
        <h3 id="journey-detail-heading" ref={headingRef} tabIndex={-1}>
          Journey details
        </h3>
        <button type="button" onClick={onClose}>
          Close details
        </button>
      </div>

      {state.status === 'loading' && (
        <p role="status">Loading journey details…</p>
      )}

      {state.status === 'error' && (
        <div className="error">
          <p role="alert">Unable to load journey details. Please try again.</p>
          <button type="button" onClick={onRetry}>
            Retry details
          </button>
        </div>
      )}

      {state.status === 'ready' && detail && (
        <>
          <h4>{detail.service_name}</h4>
          <p>
            Service date: {detail.service_date}. Status: {detail.run_status}.
          </p>

          {detail.run_status === 'cancelled' && (
            <p role="alert">
              This run is cancelled. The times below describe its original
              schedule.
            </p>
          )}

          {detail.run_status === 'restricted' && (
            <p role="status">
              This run is restricted. Its scheduled times do not establish
              whether the selected segment is unaffected.
            </p>
          )}

          {segment && (
            <p className="selection">
              Your segment: {segment.departure_station.name} to{' '}
              {segment.arrival_station.name}. Scheduled duration:{' '}
              {formatDuration(segment.duration_minutes)}.
            </p>
          )}

          <p className="muted">
            Fictional demonstration schedule. All times are in Asia/Colombo.
            Source: {detail.source_ref}. Run version: {detail.run_version}.
          </p>

          <ol className="stop-timeline">
            {detail.stops.map((stop) => {
              const selected = Boolean(
                segment &&
                  stop.stop_sequence >= segment.departure_stop_sequence &&
                  stop.stop_sequence <= segment.arrival_stop_sequence,
              )

              return (
                <li
                  key={stop.stop_sequence}
                  className={selected ? 'selected-stop' : undefined}
                >
                  <h5>
                    Stop {stop.stop_sequence}: {stop.station.name}
                  </h5>

                  {selected && <p className="muted">Within your segment</p>}

                  <dl className="journey-details">
                    <div>
                      <dt>Scheduled arrival</dt>
                      <dd>
                        {stop.scheduled_arrival_at ? (
                          <time dateTime={stop.scheduled_arrival_at}>
                            {formatJourneyTimestamp(stop.scheduled_arrival_at)}
                          </time>
                        ) : (
                          'Not applicable'
                        )}
                      </dd>
                    </div>
                    <div>
                      <dt>Scheduled departure</dt>
                      <dd>
                        {stop.scheduled_departure_at ? (
                          <time dateTime={stop.scheduled_departure_at}>
                            {formatJourneyTimestamp(stop.scheduled_departure_at)}
                          </time>
                        ) : (
                          'Not applicable'
                        )}
                      </dd>
                    </div>
                    <div>
                      <dt>Passenger permissions</dt>
                      <dd>
                        Boarding: {stop.pickup_allowed ? 'allowed' : 'not allowed'}.
                        {' '}Alighting: {stop.dropoff_allowed ? 'allowed' : 'not allowed'}.
                      </dd>
                    </div>
                  </dl>
                </li>
              )
            })}
          </ol>
        </>
      )}
    </section>
  )
}
