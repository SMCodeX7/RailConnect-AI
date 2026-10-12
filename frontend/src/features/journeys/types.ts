import type { Station } from '../stations/types'

export interface JourneySearchInput {
  departureStationId: string
  arrivalStationId: string
  travelDate: string
  arriveBefore?: string
  arrivalDate?: string
  limit?: number
  offset?: number
}

export interface Journey {
  run_id: string
  service_date: string
  run_version: number
  run_status: 'scheduled' | 'restricted'
  departure_stop_sequence: number
  arrival_stop_sequence: number
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

export interface JourneyDetailInput {
  runId: string
  departureStopSequence: number
  arrivalStopSequence: number
}

export interface JourneyStop {
  stop_sequence: number
  station: Station
  scheduled_arrival_at: string | null
  scheduled_departure_at: string | null
  pickup_allowed: boolean
  dropoff_allowed: boolean
}

export interface JourneySegment {
  departure_stop_sequence: number
  arrival_stop_sequence: number
  departure_station: Station
  arrival_station: Station
  scheduled_departure_at: string
  scheduled_arrival_at: string
  duration_minutes: number
}

export interface JourneyDetailResponse {
  data_kind: 'demonstration'
  timezone: 'Asia/Colombo'
  run_id: string
  service_id: string
  service_code: string
  service_name: string
  service_date: string
  run_version: number
  run_status: 'scheduled' | 'cancelled' | 'restricted'
  source_ref: string
  stops: JourneyStop[]
  selected_segment: JourneySegment | null
}
