import { beforeEach, describe, expect, it, vi } from 'vitest'

import { getJson } from '../../shared/api/http'
import { getJourneys } from './api'
import type { JourneyListResponse, JourneySearchInput } from './types'

vi.mock('../../shared/api/http', () => ({
  getJson: vi.fn(),
}))

const input: JourneySearchInput = {
  departureStationId: 'b6720497-5253-5d39-9f98-25bd1a1fec44',
  arrivalStationId: '02eb7cbc-e6b1-5f00-849f-da81724d34cf',
  travelDate: '2026-10-12',
}

const result: JourneyListResponse = {
  data_kind: 'demonstration',
  timezone: 'Asia/Colombo',
  departure_station_id: input.departureStationId,
  arrival_station_id: input.arrivalStationId,
  travel_date: input.travelDate,
  items: [],
  total: 0,
  limit: 50,
  offset: 0,
}

const mockedGetJson = vi.mocked(getJson)

beforeEach(() => {
  vi.resetAllMocks()
  mockedGetJson.mockResolvedValue(result)
})

describe('getJourneys', () => {
  it('maps form values to the backend query contract', async () => {
    const controller = new AbortController()

    const response = await getJourneys(input, controller.signal)
    const call = mockedGetJson.mock.calls.at(0)
    const url = new URL(call?.[0] ?? '', 'http://localhost')

    expect(url.pathname).toBe('/api/v1/journeys')
    expect(url.searchParams.get('departure_station_id')).toBe(
      input.departureStationId,
    )
    expect(url.searchParams.get('arrival_station_id')).toBe(
      input.arrivalStationId,
    )
    expect(url.searchParams.get('travel_date')).toBe(input.travelDate)
    expect(url.searchParams.get('limit')).toBe('50')
    expect(url.searchParams.get('offset')).toBe('0')
    expect(call?.[1]).toBe(controller.signal)
    expect(response).toEqual(result)
  })

  it('passes explicit pagination values', async () => {
    const controller = new AbortController()

    await getJourneys(
      { ...input, limit: 10, offset: 20 },
      controller.signal,
    )

    const call = mockedGetJson.mock.calls.at(0)
    const url = new URL(call?.[0] ?? '', 'http://localhost')

    expect(url.searchParams.get('limit')).toBe('10')
    expect(url.searchParams.get('offset')).toBe('20')
    expect(call?.[1]).toBe(controller.signal)
  })
})
