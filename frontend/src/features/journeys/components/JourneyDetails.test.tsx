import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { getStations } from '../../stations/api'
import type { Station } from '../../stations/types'
import { getJourneyDetail, getJourneys } from '../api'
import type {
  Journey,
  JourneyDetailResponse,
  JourneyListResponse,
} from '../types'
import { JourneyResults } from './JourneyResults'
import { JourneyStationPicker } from './JourneyStationPicker'

vi.mock('../../stations/api', () => ({
  getStations: vi.fn(),
}))

vi.mock('../api', () => ({
  getJourneys: vi.fn(),
  getJourneyDetail: vi.fn(),
}))

const departure: Station = {
  id: '10000000-0000-4000-8000-000000000001',
  code: 'DEMO_FORT',
  name: 'Colombo Fort',
  source_ref: 'demo-stations-v1',
  is_active: true,
}

const arrival: Station = {
  id: '10000000-0000-4000-8000-000000000002',
  code: 'DEMO_JAFFNA',
  name: 'Jaffna',
  source_ref: 'demo-stations-v1',
  is_active: true,
}

const journey: Journey = {
  source: null,
  run_id: '20000000-0000-4000-8000-000000000001',
  service_id: '30000000-0000-4000-8000-000000000001',
  service_code: 'DEMO_NORTH_OUT',
  service_name: 'Demo Northern Outbound',
  service_date: '2026-10-12',
  run_version: 1,
  run_status: 'scheduled',
  source_ref: 'demo-timetable-v1',
  departure_stop_sequence: 1,
  arrival_stop_sequence: 2,
  departure_station: departure,
  arrival_station: arrival,
  departure_at: '2026-10-12T06:00:00+05:30',
  arrival_at: '2026-10-12T15:00:00+05:30',
  duration_minutes: 540,
}

const results: JourneyListResponse = {
  data_kind: 'demonstration',
  timezone: 'Asia/Colombo',
  departure_station_id: departure.id,
  arrival_station_id: arrival.id,
  travel_date: '2026-10-12',
  items: [journey],
  total: 1,
  limit: 50,
  offset: 0,
}

function makeDetail(target: Journey): JourneyDetailResponse {
  return {
    data_kind: 'demonstration',
    timezone: 'Asia/Colombo',
    run_id: target.run_id,
    service_id: target.service_id,
    service_code: target.service_code,
    service_name: target.service_name,
    service_date: target.service_date,
    run_version: target.run_version,
    run_status: target.run_status,
    source_ref: target.source_ref,
    source: target.source,
    stops: [
      {
        stop_sequence: 1,
        station: departure,
        scheduled_arrival_at: null,
        scheduled_departure_at: target.departure_at,
        pickup_allowed: true,
        dropoff_allowed: false,
      },
      {
        stop_sequence: 2,
        station: arrival,
        scheduled_arrival_at: target.arrival_at,
        scheduled_departure_at: null,
        pickup_allowed: false,
        dropoff_allowed: true,
      },
    ],
    selected_segment: {
      departure_stop_sequence: 1,
      arrival_stop_sequence: 2,
      departure_station: departure,
      arrival_station: arrival,
      scheduled_departure_at: target.departure_at,
      scheduled_arrival_at: target.arrival_at,
      duration_minutes: target.duration_minutes,
    },
  }
}

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((resolvePromise) => {
    resolve = resolvePromise
  })
  return { promise, resolve }
}

async function prepareSearch() {
  const user = userEvent.setup()
  render(<JourneyStationPicker />)

  const departureSelect = screen.getByRole('combobox', {
    name: 'Departure station',
  })

  await waitFor(() => expect(departureSelect).toBeEnabled())
  await user.selectOptions(departureSelect, departure.id)
  await user.selectOptions(
    screen.getByRole('combobox', { name: 'Arrival station' }),
    arrival.id,
  )
  fireEvent.change(screen.getByLabelText('Travel date'), {
    target: { value: '2026-10-12' },
  })

  return user
}

const mockedDetails = vi.mocked(getJourneyDetail)
const mockedJourneys = vi.mocked(getJourneys)

beforeEach(() => {
  vi.resetAllMocks()
  vi.mocked(getStations).mockResolvedValue([departure, arrival])
  mockedJourneys.mockResolvedValue(results)
  mockedDetails.mockResolvedValue(makeDetail(journey))
})

describe('Journey details', () => {
  it('requests the run and selected segment and displays ordered stops', async () => {
    const user = userEvent.setup()
    render(<JourneyResults result={results} onPageChange={vi.fn()} />)

    await user.click(screen.getByRole('button', {
      name: 'View journey details for Demo Northern Outbound',
    }))

    const panel = screen.getByRole('region', { name: 'Journey details' })
    await within(panel).findByRole('heading', { name: journey.service_name })

    expect(mockedDetails).toHaveBeenCalledWith(
      {
        runId: journey.run_id,
        departureStopSequence: 1,
        arrivalStopSequence: 2,
      },
      expect.any(AbortSignal),
    )

    const stops = within(panel).getAllByRole('listitem')
    expect(within(stops[0]).getByRole('heading')).toHaveTextContent('Colombo Fort')
    expect(within(stops[1]).getByRole('heading')).toHaveTextContent('Jaffna')
    expect(within(panel).getByText(/Scheduled duration: 9 h/)).toBeInTheDocument()
    expect(within(panel).getByText(/Source: demo-timetable-v1/)).toBeInTheDocument()
  })

  it('shows loading until the detail request completes', async () => {
    const pending = deferred<JourneyDetailResponse>()
    mockedDetails.mockReturnValueOnce(pending.promise)
    const user = userEvent.setup()
    render(<JourneyResults result={results} onPageChange={vi.fn()} />)

    await user.click(screen.getByRole('button', {
      name: 'View journey details for Demo Northern Outbound',
    }))

    expect(screen.getByText('Loading journey details…')).toBeInTheDocument()

    await act(async () => {
      pending.resolve(makeDetail(journey))
    })

    await waitFor(() => {
      expect(screen.queryByText('Loading journey details…')).not.toBeInTheDocument()
    })
  })

  it('retries a failed detail request', async () => {
    mockedDetails.mockRejectedValueOnce(new Error('Network failure'))
    const user = userEvent.setup()
    render(<JourneyResults result={results} onPageChange={vi.fn()} />)

    await user.click(screen.getByRole('button', {
      name: 'View journey details for Demo Northern Outbound',
    }))
    await screen.findByRole('alert')
    await user.click(screen.getByRole('button', { name: 'Retry details' }))

    const panel = screen.getByRole('region', { name: 'Journey details' })
    await within(panel).findByRole('heading', { name: journey.service_name })
    expect(mockedDetails).toHaveBeenCalledTimes(2)
    expect(within(panel).queryByRole('alert')).not.toBeInTheDocument()
  })

  it('closes details, cancels the request and restores focus', async () => {
    const pending = deferred<JourneyDetailResponse>()
    mockedDetails.mockReturnValueOnce(pending.promise)
    const user = userEvent.setup()
    render(<JourneyResults result={results} onPageChange={vi.fn()} />)

    const button = screen.getByRole('button', {
      name: 'View journey details for Demo Northern Outbound',
    })
    await user.click(button)

    const signal = mockedDetails.mock.calls[0][1]
    await user.click(screen.getByRole('button', { name: 'Close details' }))

    expect(signal.aborted).toBe(true)
    expect(button).toHaveFocus()
    expect(screen.queryByRole('region', {
      name: 'Journey details',
    })).not.toBeInTheDocument()

    await act(async () => {
      pending.resolve(makeDetail(journey))
    })

    expect(screen.queryByRole('region', {
      name: 'Journey details',
    })).not.toBeInTheDocument()
  })

  it('ignores an old response after another journey is opened', async () => {
    const pending = deferred<JourneyDetailResponse>()
    const second: Journey = {
      ...journey,
      run_id: '20000000-0000-4000-8000-000000000002',
      service_name: 'Another Service',
    }
    mockedDetails
      .mockReturnValueOnce(pending.promise)
      .mockResolvedValueOnce(makeDetail(second))

    const user = userEvent.setup()
    render(
      <JourneyResults
        result={{ ...results, items: [journey, second], total: 2 }}
        onPageChange={vi.fn()}
      />,
    )

    await user.click(screen.getByRole('button', {
      name: 'View journey details for Demo Northern Outbound',
    }))
    const oldSignal = mockedDetails.mock.calls[0][1]

    await user.click(screen.getByRole('button', {
      name: 'View journey details for Another Service',
    }))

    const panel = screen.getByRole('region', { name: 'Journey details' })
    await within(panel).findByRole('heading', { name: 'Another Service' })
    expect(oldSignal.aborted).toBe(true)

    await act(async () => {
      pending.resolve(makeDetail(journey))
    })

    expect(within(panel).getByRole('heading', {
      name: 'Another Service',
    })).toBeInTheDocument()
    expect(within(panel).queryByRole('heading', {
      name: journey.service_name,
    })).not.toBeInTheDocument()
  })

  it('shows cancellation received from the detail endpoint', async () => {
    mockedDetails.mockResolvedValueOnce({
      ...makeDetail(journey),
      run_status: 'cancelled',
      run_version: 2,
    })
    const user = userEvent.setup()
    render(<JourneyResults result={results} onPageChange={vi.fn()} />)

    await user.click(screen.getByRole('button', {
      name: 'View journey details for Demo Northern Outbound',
    }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'This run is cancelled',
    )
  })

  it('cancels detail loading when the results unmount', async () => {
    const pending = deferred<JourneyDetailResponse>()
    mockedDetails.mockReturnValueOnce(pending.promise)
    const user = userEvent.setup()
    const { unmount } = render(
      <JourneyResults result={results} onPageChange={vi.fn()} />,
    )

    await user.click(screen.getByRole('button', {
      name: 'View journey details for Demo Northern Outbound',
    }))
    const signal = mockedDetails.mock.calls[0][1]
    unmount()

    expect(signal.aborted).toBe(true)

    await act(async () => {
      pending.resolve(makeDetail(journey))
    })
  })
})

describe('Arrival deadline controls', () => {
  it('submits an explicit arrival time and date', async () => {
    const user = await prepareSearch()

    fireEvent.change(screen.getByLabelText('Arrive by'), {
      target: { value: '06:00' },
    })
    fireEvent.change(screen.getByLabelText('Arrival deadline date'), {
      target: { value: '2026-10-13' },
    })
    await user.click(screen.getByRole('button', { name: 'Search journeys' }))

    expect(mockedJourneys).toHaveBeenCalledWith(
      {
        departureStationId: departure.id,
        arrivalStationId: arrival.id,
        travelDate: '2026-10-12',
        arriveBefore: '06:00',
        arrivalDate: '2026-10-13',
        offset: 0,
      },
      expect.any(AbortSignal),
    )
  })

  it('omits the arrival date when only a time is supplied', async () => {
    const user = await prepareSearch()

    fireEvent.change(screen.getByLabelText('Arrive by'), {
      target: { value: '15:00' },
    })
    await user.click(screen.getByRole('button', { name: 'Search journeys' }))

    const input = mockedJourneys.mock.calls[0][0]
    expect(input.arriveBefore).toBe('15:00')
    expect(input).not.toHaveProperty('arrivalDate')
  })

  it('clears both deadline values when the time is removed', async () => {
    const user = await prepareSearch()

    fireEvent.change(screen.getByLabelText('Arrive by'), {
      target: { value: '06:00' },
    })
    const dateInput = screen.getByLabelText('Arrival deadline date')
    fireEvent.change(dateInput, { target: { value: '2026-10-13' } })
    fireEvent.change(screen.getByLabelText('Arrive by'), {
      target: { value: '' },
    })

    expect(dateInput).toHaveValue('')
    expect(dateInput).toBeDisabled()

    await user.click(screen.getByRole('button', { name: 'Search journeys' }))
    const input = mockedJourneys.mock.calls[0][0]
    expect(input).not.toHaveProperty('arriveBefore')
    expect(input).not.toHaveProperty('arrivalDate')
  })

  it('rejects an arrival date before the travel date', async () => {
    await prepareSearch()

    fireEvent.change(screen.getByLabelText('Arrive by'), {
      target: { value: '06:00' },
    })
    fireEvent.change(screen.getByLabelText('Arrival deadline date'), {
      target: { value: '2026-10-11' },
    })

    expect(screen.getByRole('alert')).toHaveTextContent(
      'cannot precede the travel date',
    )
    expect(screen.getByRole('button', {
      name: 'Search journeys',
    })).toBeDisabled()
    expect(mockedJourneys).not.toHaveBeenCalled()
  })

  it('clears previous results when the deadline changes', async () => {
    const user = await prepareSearch()
    await user.click(screen.getByRole('button', { name: 'Search journeys' }))
    await screen.findByRole('heading', { name: journey.service_name })

    fireEvent.change(screen.getByLabelText('Arrive by'), {
      target: { value: '14:00' },
    })

    expect(screen.queryByRole('heading', {
      name: journey.service_name,
    })).not.toBeInTheDocument()
    expect(mockedJourneys).toHaveBeenCalledTimes(1)
  })
})
