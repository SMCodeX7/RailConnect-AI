import { getJson } from '../../shared/api/http'
import type { JourneyListResponse, JourneySearchInput } from './types'

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

  return getJson<JourneyListResponse>(
    `/api/v1/journeys?${parameters.toString()}`,
    signal,
  )
}
