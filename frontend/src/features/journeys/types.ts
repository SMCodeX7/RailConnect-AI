import type { Station } from '../stations/types'

export interface TimetableSource {
  id: string
  source_ref: string
  title: string
  source_uri: string
  reuse_basis: string
  data_kind: 'demonstration' | 'observed'
  content_sha256: string
  effective_from: string
  effective_until: string
  retrieved_at: string | null
  registered_at: string
}

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
  source: TimetableSource | null
  departure_station: Station
  arrival_station: Station
  departure_at: string
  arrival_at: string
  duration_minutes: number
  disruption?: JourneyDisruption | null
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
  disruption?: JourneyDisruption | null
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
  source: TimetableSource | null
  stops: JourneyStop[]
  selected_segment: JourneySegment | null
}

export interface JourneyDisruption {
  cancelled: boolean
  restricted: boolean
  estimated_departure_at: string | null
  estimated_arrival_at: string | null
  effects: {
    incident_id: string
    revision_id: string
    impact_kind: 'cancellation' | 'restriction' | 'delay'
  }[]
}

export interface JourneyAlternativesInput extends JourneyDetailInput {
  arriveBefore?: string
  arrivalDate?: string
}

export interface JourneyAlternativesResponse {
  original_run_id: string
  items: Journey[]
  total: number
  explanation: string
}
