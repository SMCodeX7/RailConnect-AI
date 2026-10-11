import { useState } from 'react'

import { StationSelect } from '../../stations/components/StationSelect'
import { useStations } from '../../stations/hooks/useStations'

export function JourneyStationPicker() {
  const { stations, status, retry } = useStations()
  const [departureId, setDepartureId] = useState('')
  const [arrivalId, setArrivalId] = useState('')

  const departure = stations.find((station) => station.id === departureId)
  const arrival = stations.find((station) => station.id === arrivalId)
  const disabled = status !== 'ready' || stations.length === 0

  return (
    <section className="card" aria-labelledby="journey-heading">
      <h2 id="journey-heading">Choose your journey</h2>
      <p>Select your departure and arrival stations.</p>

      {status === 'loading' && (
        <p role="status">Loading stations…</p>
      )}

      {status === 'error' && (
        <div className="error">
          <p role="alert">Unable to load stations. Please try again.</p>
          <button type="button" onClick={retry}>
            Retry
          </button>
        </div>
      )}

      {status === 'ready' && stations.length === 0 && (
        <p role="status">No stations are currently available.</p>
      )}

      <div className="station-grid">
        <StationSelect
          id="departure-station"
          label="Departure station"
          value={departureId}
          stations={stations}
          excludedId={arrivalId}
          disabled={disabled}
          onChange={setDepartureId}
        />
        <StationSelect
          id="arrival-station"
          label="Arrival station"
          value={arrivalId}
          stations={stations}
          excludedId={departureId}
          disabled={disabled}
          onChange={setArrivalId}
        />
      </div>

      {departure && arrival && (
        <p className="selection" role="status">
          Selected journey: <strong>{departure.name}</strong> to{' '}
          <strong>{arrival.name}</strong>.
        </p>
      )}

      <p className="muted">
        Journey timetable search will be added in the next development phase.
      </p>
    </section>
  )
}
