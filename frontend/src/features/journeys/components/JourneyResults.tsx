import { formatDuration, formatJourneyTimestamp } from '../formatting'
import type { JourneyListResponse } from '../types'

interface JourneyResultsProps {
  result: JourneyListResponse
  onPageChange: (offset: number) => void
}

export function JourneyResults({
  result,
  onPageChange,
}: JourneyResultsProps) {
  const hasPrevious = result.offset > 0
  const hasNext = result.offset + result.limit < result.total

  return (
    <section
      className="journey-results"
      aria-labelledby="journey-results-heading"
    >
      <h3 id="journey-results-heading">Journey results</h3>

      {result.total === 0 ? (
        <p role="status">
          No direct services found for these stations on the selected date.
          Try another date or station pair.
        </p>
      ) : result.items.length === 0 ? (
        <p role="status">No journeys on this page. Return to the previous page.</p>
      ) : (
        <p role="status">
          Showing {result.offset + 1}–
          {result.offset + result.items.length} of {result.total} journeys.
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
                key={`${journey.service_id}:${journey.departure_at}:${journey.arrival_at}`}
              >
                <article className="journey-result">
                  <h4>{journey.service_name}</h4>

                  <p>
                    {journey.departure_station.name} to{' '}
                    {journey.arrival_station.name}
                  </p>

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
                </article>
              </li>
            ))}
          </ul>
        </>
      )}

      {(hasPrevious || hasNext) && (
        <nav className="pagination" aria-label="Journey result pages">
          <button
            type="button"
            disabled={!hasPrevious}
            onClick={() =>
              onPageChange(Math.max(0, result.offset - result.limit))
            }
          >
            Previous
          </button>

          <button
            type="button"
            disabled={!hasNext}
            onClick={() => onPageChange(result.offset + result.limit)}
          >
            Next
          </button>
        </nav>
      )}
    </section>
  )
}
