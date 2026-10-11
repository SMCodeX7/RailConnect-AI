import { useState } from 'react'
import type { FormEvent } from 'react'

import { StationSelect } from '../../stations/components/StationSelect'
import { useStations } from '../../stations/hooks/useStations'
import { getColomboToday } from '../formatting'
import { useJourneys } from '../hooks/useJourneys'
import { JourneyResults } from './JourneyResults'

export function JourneyStationPicker() {
  const { stations, status, retry } = useStations()
  const journeys = useJourneys()

  const [departureId, setDepartureId] = useState('')
  const [arrivalId, setArrivalId] = useState('')
  const [travelDate, setTravelDate] = useState(getColomboToday)

  const departure = stations.find((station) => station.id === departureId)
  const arrival = stations.find((station) => station.id === arrivalId)
  const disabled = status !== 'ready' || stations.length === 0

  const canSearch =
    !disabled &&
    Boolean(departure && arrival) &&
    departureId !== arrivalId &&
    /^\d{4}-\d{2}-\d{2}$/.test(travelDate)

  function changeDeparture(value: string) {
    setDepartureId(value)
    journeys.reset()
  }

  function changeArrival(value: string) {
    setArrivalId(value)
    journeys.reset()
  }

  function changeDate(value: string) {
    setTravelDate(value)
    journeys.reset()
  }

  function runSearch(offset = 0) {
    if (!canSearch || journeys.status === 'loading') return

    void journeys.search({
      departureStationId: departureId,
      arrivalStationId: arrivalId,
      travelDate,
      offset,
    })
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    runSearch()
  }

  return (
    <section className="card" aria-labelledby="journey-heading">
      <h2 id="journey-heading">Find a direct journey</h2>
      <p>Select your stations and boarding date.</p>

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

      <form onSubmit={handleSubmit}>
        <div className="station-grid">
          <StationSelect
            id="departure-station"
            label="Departure station"
            value={departureId}
            stations={stations}
            excludedId={arrivalId}
            disabled={disabled}
            onChange={changeDeparture}
          />

          <StationSelect
            id="arrival-station"
            label="Arrival station"
            value={arrivalId}
            stations={stations}
            excludedId={departureId}
            disabled={disabled}
            onChange={changeArrival}
          />
        </div>

        <div className="journey-actions">
          <div className="field">
            <label htmlFor="travel-date">Travel date</label>
            <input
              id="travel-date"
              type="date"
              value={travelDate}
              disabled={disabled}
              required
              onChange={(event) => changeDate(event.target.value)}
            />
          </div>

          <button
            type="submit"
            disabled={!canSearch || journeys.status === 'loading'}
          >
            {journeys.status === 'loading' ? 'Searching…' : 'Search journeys'}
          </button>
        </div>
      </form>

      {departure && arrival && (
        <p className="selection" role="status">
          Selected journey: <strong>{departure.name}</strong> to{' '}
          <strong>{arrival.name}</strong>.
        </p>
      )}

      <div className="journey-feedback">
        {journeys.status === 'loading' && (
          <p role="status">Searching demonstration timetables…</p>
        )}

        {journeys.status === 'error' && (
          <div className="error">
            <p role="alert">Unable to search journeys. Please try again.</p>
            <button type="button" onClick={() => runSearch()}>
              Retry search
            </button>
          </div>
        )}

        {journeys.status === 'ready' && journeys.result && (
          <JourneyResults
            result={journeys.result}
            onPageChange={runSearch}
          />
        )}
      </div>
    </section>
  )
}
