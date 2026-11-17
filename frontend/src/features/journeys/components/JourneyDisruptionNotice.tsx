import { formatJourneyTimestamp } from '../formatting'
import type { JourneyDisruption } from '../types'

export function JourneyDisruptionNotice({
  disruption,
}: {
  disruption?: JourneyDisruption | null
}) {
  if (!disruption) return null

  if (disruption.cancelled) {
    return <p role="alert">A verified cancellation affects this segment.</p>
  }

  if (disruption.restricted) {
    return <p role="alert">A verified restriction makes this segment unavailable.</p>
  }

  const departure = disruption.estimated_departure_at
  const arrival = disruption.estimated_arrival_at

  return (
    <div className="journey-delay-notice">
      <p>Verified delay affecting this segment.</p>
      <dl className="journey-details">
        {departure && (
          <div>
            <dt>Estimated departure</dt>
            <dd><time dateTime={departure}>{formatJourneyTimestamp(departure)}</time></dd>
          </div>
        )}
        {arrival && (
          <div>
            <dt>Estimated arrival</dt>
            <dd><time dateTime={arrival}>{formatJourneyTimestamp(arrival)}</time></dd>
          </div>
        )}
      </dl>
    </div>
  )
}
