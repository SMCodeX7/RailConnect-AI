import { act, fireEvent, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { getStations } from '../../stations/api'
import type { Station } from '../../stations/types'
import { getJourneys } from '../api'
import type { Journey, JourneyListResponse } from '../types'
import { JourneyStationPicker } from './JourneyStationPicker'

vi.mock('../../stations/api', () => ({
  getStations: vi.fn(),
}))

vi.mock('../api', () => ({
  getJourneys: vi.fn(),
  getJourneyDetail: vi.fn(),
}))

const fort: Station = {
  id: 'b6720497-5253-5d39-9f98-25bd1a1fec44',
  code: 'DEMO_FORT',
  name: 'Colombo Fort',
  source_ref: 'demo-stations-v1',
  is_active: true,
}

const jaffna: Station = {
  id: '02eb7cbc-e6b1-5f00-849f-da81724d34cf',
  code: 'DEMO_JAFFNA',
  name: 'Jaffna',
  source_ref: 'demo-stations-v1',
  is_active: true,
}

const trincomalee: Station = {
  id: '64d9b52f-5e92-5974-99bc-ad1b7b2aefab',
  code: 'DEMO_TRINCOMALEE',
  name: 'Trincomalee',
  source_ref: 'demo-stations-v1',
  is_active: true,
}

const journey: Journey = {
  source: null,
  run_id: '20000000-0000-4000-8000-000000000001',
  service_date: '2026-10-12',
  run_version: 1,
  run_status: 'scheduled',
  departure_stop_sequence: 1,
  arrival_stop_sequence: 3,
  service_id: '10000000-0000-4000-8000-000000000001',
  service_code: 'DEMO_NORTH_OUT',
  service_name: 'Demo Northern Outbound',
  source_ref: 'demo-timetable-v1',
  departure_station: fort,
  arrival_station: jaffna,
  departure_at: '2026-10-12T06:00:00+05:30',
  arrival_at: '2026-10-12T15:00:00+05:30',
  duration_minutes: 540,
}

const result: JourneyListResponse = {
  data_kind: 'demonstration',
  timezone: 'Asia/Colombo',
  departure_station_id: fort.id,
  arrival_station_id: jaffna.id,
  travel_date: '2026-10-12',
  items: [journey],
  total: 1,
  limit: 50,
  offset: 0,
}

const mockedGetStations = vi.mocked(getStations)
const mockedGetJourneys = vi.mocked(getJourneys)

function deferred<T>() {
  let resolve!: (value: T) => void

  const promise = new Promise<T>((resolvePromise) => {
    resolve = resolvePromise
  })

  return { promise, resolve }
}

async function prepareJourney() {
  const user = userEvent.setup()
  const { unmount } = render(<JourneyStationPicker />)

  const departure = screen.getByRole('combobox', {
    name: 'Departure station',
  })
  const arrival = screen.getByRole('combobox', {
    name: 'Arrival station',
  })
  const dateInput = screen.getByLabelText('Travel date')

  await waitFor(() => expect(departure).toBeEnabled())
  await user.selectOptions(departure, fort.id)
  await user.selectOptions(arrival, jaffna.id)

  fireEvent.change(dateInput, {
    target: { value: '2026-10-12' },
  })

  return { user, departure, arrival, dateInput, unmount }
}

beforeEach(() => {
  vi.resetAllMocks()
  mockedGetStations.mockResolvedValue([fort, jaffna, trincomalee])
  mockedGetJourneys.mockResolvedValue(result)
})

describe('Journey search', () => {
  it('requires both stations and a date before searching', async () => {
    const user = userEvent.setup()
    render(<JourneyStationPicker />)

    const departure = screen.getByRole('combobox', {
      name: 'Departure station',
    })
    const arrival = screen.getByRole('combobox', {
      name: 'Arrival station',
    })
    const button = screen.getByRole('button', {
      name: 'Search journeys',
    })

    expect(button).toBeDisabled()

    await waitFor(() => expect(departure).toBeEnabled())
    await user.selectOptions(departure, fort.id)
    expect(button).toBeDisabled()

    await user.selectOptions(arrival, jaffna.id)
    expect(button).toBeEnabled()

    fireEvent.change(screen.getByLabelText('Travel date'), {
      target: { value: '' },
    })

    expect(button).toBeDisabled()
    expect(mockedGetJourneys).not.toHaveBeenCalled()
  })

  it('submits the selected journey and displays its result', async () => {
    const { user } = await prepareJourney()

    await user.click(
      screen.getByRole('button', { name: 'Search journeys' }),
    )

    expect(
      await screen.findByRole('heading', {
        name: 'Demo Northern Outbound',
      }),
    ).toBeInTheDocument()

    expect(mockedGetJourneys).toHaveBeenCalledWith(
      {
        departureStationId: fort.id,
        arrivalStationId: jaffna.id,
        travelDate: '2026-10-12',
        offset: 0,
      },
      expect.any(AbortSignal),
    )

    expect(screen.getByText('9 h')).toBeInTheDocument()
    expect(
      screen.getByText(/Fictional demonstration schedules/),
    ).toBeInTheDocument()
  })

  it('shows loading and prevents repeated submission', async () => {
    const pending = deferred<JourneyListResponse>()
    mockedGetJourneys.mockReturnValueOnce(pending.promise)
    const { user } = await prepareJourney()

    await user.click(
      screen.getByRole('button', { name: 'Search journeys' }),
    )

    expect(
      screen.getByText('Searching demonstration timetables…'),
    ).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: 'Searching…' }),
    ).toBeDisabled()

    await act(async () => {
      pending.resolve(result)
    })

    expect(
      await screen.findByRole('heading', {
        name: 'Demo Northern Outbound',
      }),
    ).toBeInTheDocument()
    expect(mockedGetJourneys).toHaveBeenCalledTimes(1)
  })

  it('recovers from a search failure using Retry search', async () => {
    mockedGetJourneys.mockRejectedValueOnce(new Error('Network failure'))
    const { user } = await prepareJourney()

    await user.click(
      screen.getByRole('button', { name: 'Search journeys' }),
    )

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Unable to search journeys.',
    )

    await user.click(
      screen.getByRole('button', { name: 'Retry search' }),
    )

    expect(
      await screen.findByRole('heading', {
        name: 'Demo Northern Outbound',
      }),
    ).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(mockedGetJourneys).toHaveBeenCalledTimes(2)
  })

  it('explains a search with no direct services', async () => {
    mockedGetJourneys.mockResolvedValueOnce({
      ...result,
      items: [],
      total: 0,
    })
    const { user } = await prepareJourney()

    await user.click(
      screen.getByRole('button', { name: 'Search journeys' }),
    )

    expect(
      await screen.findByText(/No direct services found/),
    ).toBeInTheDocument()
    expect(
      screen.queryByRole('heading', {
        name: 'Demo Northern Outbound',
      }),
    ).not.toBeInTheDocument()
  })

  it.each(['departure', 'arrival', 'date'])(
    'clears results when the %s changes',
    async (field) => {
      const { user, departure, arrival, dateInput } =
        await prepareJourney()

      await user.click(
        screen.getByRole('button', { name: 'Search journeys' }),
      )

      await screen.findByRole('heading', {
        name: 'Demo Northern Outbound',
      })

      if (field === 'departure') {
        await user.selectOptions(departure, trincomalee.id)
      } else if (field === 'arrival') {
        await user.selectOptions(arrival, trincomalee.id)
      } else {
        fireEvent.change(dateInput, {
          target: { value: '2026-10-13' },
        })
      }

      expect(
        screen.queryByRole('heading', {
          name: 'Demo Northern Outbound',
        }),
      ).not.toBeInTheDocument()
      expect(mockedGetJourneys).toHaveBeenCalledTimes(1)
    },
  )

  it('ignores an older response after a new search', async () => {
    const oldRequest = deferred<JourneyListResponse>()
    const latestResult: JourneyListResponse = {
      ...result,
      travel_date: '2026-10-13',
      items: [
        {
          ...journey,
          service_name: 'New Search Service',
          departure_at: '2026-10-13T06:00:00+05:30',
          arrival_at: '2026-10-13T15:00:00+05:30',
        },
      ],
    }

    mockedGetJourneys
      .mockReturnValueOnce(oldRequest.promise)
      .mockResolvedValueOnce(latestResult)

    const { user, dateInput } = await prepareJourney()

    await user.click(
      screen.getByRole('button', { name: 'Search journeys' }),
    )

    const oldSignal = mockedGetJourneys.mock.calls.at(0)?.[1]

    fireEvent.change(dateInput, {
      target: { value: '2026-10-13' },
    })

    expect(oldSignal?.aborted).toBe(true)

    await user.click(
      screen.getByRole('button', { name: 'Search journeys' }),
    )

    await screen.findByRole('heading', { name: 'New Search Service' })

    await act(async () => {
      oldRequest.resolve(result)
    })

    expect(
      screen.getByRole('heading', { name: 'New Search Service' }),
    ).toBeInTheDocument()
    expect(
      screen.queryByRole('heading', {
        name: 'Demo Northern Outbound',
      }),
    ).not.toBeInTheDocument()
  })

  it('moves between result pages', async () => {
    const firstPage: JourneyListResponse = {
      ...result,
      total: 51,
      items: Array.from({ length: 50 }, (_, index) => ({
        ...journey,
        service_id: `10000000-0000-4000-8000-${String(index).padStart(12, '0')}`,
        service_code: `DEMO_PAGE_${index}`,
        service_name:
          index === 0 ? journey.service_name : `Demo Service ${index}`,
      })),
    }
    const secondPage: JourneyListResponse = {
      ...result,
      total: 51,
      offset: 50,
      items: [{ ...journey, service_name: 'Demo Later Service' }],
    }

    mockedGetJourneys
      .mockResolvedValueOnce(firstPage)
      .mockResolvedValueOnce(secondPage)
      .mockResolvedValueOnce(firstPage)

    const { user } = await prepareJourney()

    await user.click(
      screen.getByRole('button', { name: 'Search journeys' }),
    )

    await screen.findByRole('heading', {
      name: 'Demo Northern Outbound',
    })
    expect(
      screen.getByRole('button', { name: 'Previous' }),
    ).toBeDisabled()

    await user.click(screen.getByRole('button', { name: 'Next' }))

    await screen.findByRole('heading', { name: 'Demo Later Service' })
    expect(mockedGetJourneys.mock.calls.at(1)?.[0].offset).toBe(50)
    expect(
      screen.getByRole('button', { name: 'Next' }),
    ).toBeDisabled()

    await user.click(screen.getByRole('button', { name: 'Previous' }))

    await screen.findByRole('heading', {
      name: 'Demo Northern Outbound',
    })
    expect(mockedGetJourneys.mock.calls.at(2)?.[0].offset).toBe(0)
  })

  it('aborts a pending request when unmounted', async () => {
    const pending = deferred<JourneyListResponse>()
    mockedGetJourneys.mockReturnValueOnce(pending.promise)
    const { user, unmount } = await prepareJourney()

    await user.click(
      screen.getByRole('button', { name: 'Search journeys' }),
    )

    const signal = mockedGetJourneys.mock.calls.at(0)?.[1]
    expect(signal?.aborted).toBe(false)

    unmount()

    expect(signal?.aborted).toBe(true)

    await act(async () => {
      pending.resolve(result)
    })
  })
})
