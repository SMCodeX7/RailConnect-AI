import { useEffect, useRef, useState } from 'react'

import { getJourneyAlternatives } from '../api'
import { formatJourneyTimestamp } from '../formatting'
import type { JourneyAlternativesInput, JourneyAlternativesResponse } from '../types'
import { JourneyDisruptionNotice } from './JourneyDisruptionNotice'

export function JourneyAlternatives({ input }: { input: JourneyAlternativesInput }) {
  const request = useRef<AbortController | null>(null)
  const [result, setResult] = useState<JourneyAlternativesResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [failed, setFailed] = useState(false)

  useEffect(() => () => request.current?.abort(), [])

  async function load() {
    if (request.current) return

    const controller = new AbortController()
    request.current = controller
    setLoading(true)
    setFailed(false)
    setResult(null)

    try {
      const response = await getJourneyAlternatives(input, controller.signal)
      if (!controller.signal.aborted) setResult(response)
    } catch {
      if (!controller.signal.aborted) setFailed(true)
    } finally {
      request.current = null
      if (!controller.signal.aborted) setLoading(false)
    }
  }

  return (
    <section aria-label="Direct alternatives" aria-busy={loading}>
      <h5>Direct alternatives</h5>
      <button type="button" disabled={loading} onClick={() => void load()}>
        {loading ? 'Checking alternatives…' : 'Check direct alternatives'}
      </button>

      {failed && <p role="alert">Unable to check alternatives. Please try again.</p>}

      {result && (
        <>
          <p role="status">{result.explanation}</p>
          {result.items.length > 0 && (
            <ul className="journey-list">
              {result.items.map((journey) => (
                <li
                  key={`${journey.run_id}:${journey.departure_stop_sequence}:${journey.arrival_stop_sequence}`}
                >
                  <strong>{journey.service_name}</strong>
                  <p>
                    Scheduled departure{' '}
                    <time dateTime={journey.departure_at}>
                      {formatJourneyTimestamp(journey.departure_at)}
                    </time>
                    {' · Scheduled arrival '}
                    <time dateTime={journey.arrival_at}>
                      {formatJourneyTimestamp(journey.arrival_at)}
                    </time>
                  </p>
                  <JourneyDisruptionNotice disruption={journey.disruption} />
                </li>
              ))}
            </ul>
          )}
        </>
      )}
    </section>
  )
}
