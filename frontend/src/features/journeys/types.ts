import type { Station } from '../stations/types'

export interface JourneySearchInput {
  departureStationId: string
  arrivalStationId: string
  travelDate: string
  limit?: number
  offset?: number
}

export interface Journey {
  service_id: string
  service_code: string
  service_name: string
  source_ref: string
  departure_station: Station
  arrival_station: Station
  departure_at: string
  arrival_at: string
  duration_minutes: number
}

export interface JourneyListResponse {
  data_kind: 'demonstration'
  timezone: 'Asia/Colombo'
  departure_station_id: string
  arrival_station_id: string
  travel_date: string
  items: Journey[]
  total: number
  limit: number
  offset: number
}
