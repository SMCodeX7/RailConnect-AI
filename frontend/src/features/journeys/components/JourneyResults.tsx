import { useRef } from 'react'

import { formatDuration, formatJourneyTimestamp } from '../formatting'
import { useJourneyDetail } from '../hooks/useJourneyDetail'
import type { JourneyListResponse } from '../types'
import { JourneyDetailPanel } from './JourneyDetailPanel'

interface JourneyResultsProps {
  result: JourneyListResponse
  onPageChange: (offset: number) => void
}

export function JourneyResults({
  result,
  onPageChange,
}: JourneyResultsProps) {
  const details = useJourneyDetail()
  const triggerRef = useRef<HTMLButtonElement | null>(null)
  const hasPrevious = result.offset > 0
  const hasNext = result.offset + result.limit < result.total

  function closeDetails() {
    details.reset()
    triggerRef.current?.focus()
  }

  function changePage(offset: number) {
    details.reset()
    onPageChange(offset)
  }

  return (
    <section
      className="journey-results"
      aria-labelledby="journey-results-heading"
    >
      <h3 id="journey-results-heading">Journey results</h3>

      {result.total === 0 ? (
        <p role="status">
          No direct services found for the selected stations, date and filters.
          Try another date, station pair or arrival deadline.
        </p>
      ) : result.items.length === 0 ? (
        <p role="status">No journeys on this page. Return to the previous page.</p>
      ) : (
        <p role="status">
          Showing {result.offset + 1}–{result.offset + result.items.length}
          {' '}of {result.total} journeys.
        </p>
      )}

      {result.items.length > 0 && (
        <>
          <p className="muted">
            Fictional demonstration schedules. All times are in Sri Lanka
            time (Asia/Colombo).
          </p>

          <ul className="journey-list">
            {result.items.map((journey) => (
              <li
                key={`${journey.run_id}:${journey.service_id}:${journey.departure_stop_sequence}:${journey.arrival_stop_sequence}`}
              >
                <article className="journey-result">
                  <h4>{journey.service_name}</h4>

                  <p>
                    {journey.departure_station.name} to{' '}
                    {journey.arrival_station.name}
                  </p>
                  <p className="muted">
                    Service date: {journey.service_date}.
                    {' '}Status: {journey.run_status}.
                  </p>

                  {journey.run_status === 'restricted' && (
                    <p>
                      Restrictions apply. Review the details before choosing
                      this journey.
                    </p>
                  )}

                  <dl className="journey-details">
                    <div>
                      <dt>Departure</dt>
                      <dd>
                        <time dateTime={journey.departure_at}>
                          {formatJourneyTimestamp(journey.departure_at)}
                        </time>
                      </dd>
                    </div>
                    <div>
                      <dt>Arrival</dt>
                      <dd>
                        <time dateTime={journey.arrival_at}>
                          {formatJourneyTimestamp(journey.arrival_at)}
                        </time>
                      </dd>
                    </div>
                    <div>
                      <dt>Duration</dt>
                      <dd>{formatDuration(journey.duration_minutes)}</dd>
                    </div>
                  </dl>

                  <button
                    type="button"
                    aria-label={`View journey details for ${journey.service_name}`}
                    onClick={(event) => {
                      triggerRef.current = event.currentTarget
                      void details.load(journey)
                    }}
                  >
                    View journey details
                  </button>
                </article>
              </li>
            ))}
          </ul>
        </>
      )}

      {details.status !== 'idle' && (
        <JourneyDetailPanel
          state={details}
          onRetry={details.retry}
          onClose={closeDetails}
        />
      )}

      {(hasPrevious || hasNext) && (
        <nav className="pagination" aria-label="Journey result pages">
          <button
            type="button"
            disabled={!hasPrevious}
            onClick={() => changePage(Math.max(0, result.offset - result.limit))}
          >
            Previous
          </button>
          <button
            type="button"
            disabled={!hasNext}
            onClick={() => changePage(result.offset + result.limit)}
          >
            Next
          </button>
        </nav>
      )}
    </section>
  )
}
