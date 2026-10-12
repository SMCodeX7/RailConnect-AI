import { getJson } from '../../shared/api/http'
import type {
  JourneyDetailInput,
  JourneyDetailResponse,
  JourneyListResponse,
  JourneySearchInput,
} from './types'

export function getJourneys(
  input: JourneySearchInput,
  signal: AbortSignal,
): Promise<JourneyListResponse> {
  const parameters = new URLSearchParams({
    departure_station_id: input.departureStationId,
    arrival_station_id: input.arrivalStationId,
    travel_date: input.travelDate,
    limit: String(input.limit ?? 50),
    offset: String(input.offset ?? 0),
  })

  if (input.arriveBefore) {
    parameters.set('arrive_before', input.arriveBefore)
  }

  if (input.arrivalDate) {
    parameters.set('arrival_date', input.arrivalDate)
  }

  return getJson<JourneyListResponse>(
    `/api/v1/journeys?${parameters.toString()}`,
    signal,
  )
}

export function getJourneyDetail(
  input: JourneyDetailInput,
  signal: AbortSignal,
): Promise<JourneyDetailResponse> {
  const parameters = new URLSearchParams({
    departure_stop_sequence: String(input.departureStopSequence),
    arrival_stop_sequence: String(input.arrivalStopSequence),
  })

  return getJson<JourneyDetailResponse>(
    `/api/v1/journeys/${encodeURIComponent(input.runId)}?${parameters.toString()}`,
    signal,
  )
}
