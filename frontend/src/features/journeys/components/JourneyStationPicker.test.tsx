import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { getStations } from '../../stations/api'
import type { Station } from '../../stations/types'
import { JourneyStationPicker } from './JourneyStationPicker'

vi.mock('../../stations/api', () => ({
  getStations: vi.fn(),
}))

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

const mockedGetStations = vi.mocked(getStations)

async function renderLoadedPicker() {
  render(<JourneyStationPicker />)

  await waitFor(() => {
    expect(
      screen.getByRole('combobox', { name: 'Departure station' }),
    ).toBeEnabled()
  })

  return {
    departure: screen.getByRole('combobox', {
      name: 'Departure station',
    }),
    arrival: screen.getByRole('combobox', {
      name: 'Arrival station',
    }),
  }
}

beforeEach(() => {
  vi.resetAllMocks()
  mockedGetStations.mockResolvedValue([jaffna, trincomalee])
})

describe('JourneyStationPicker', () => {
  it('shows loading before enabling the station selectors', async () => {
    render(<JourneyStationPicker />)

    expect(screen.getByRole('status')).toHaveTextContent('Loading stations')
    expect(
      screen.getByRole('combobox', { name: 'Departure station' }),
    ).toBeDisabled()
    expect(
      screen.getByRole('combobox', { name: 'Arrival station' }),
    ).toBeDisabled()

    await waitFor(() => {
      expect(
        screen.getByRole('combobox', { name: 'Departure station' }),
      ).toBeEnabled()
    })

    expect(screen.getAllByRole('option', { name: 'Jaffna' })).toHaveLength(2)
    expect(
      screen.getAllByRole('option', { name: 'Trincomalee' }),
    ).toHaveLength(2)
  })

  it('displays the selected departure and arrival', async () => {
    const user = userEvent.setup()
    const { departure, arrival } = await renderLoadedPicker()

    await user.selectOptions(departure, jaffna.id)
    await user.selectOptions(arrival, trincomalee.id)

    expect(screen.getByRole('status')).toHaveTextContent(
      'Selected journey: Jaffna to Trincomalee.',
    )
  })

  it('disables duplicate station choices in both directions', async () => {
    const user = userEvent.setup()
    const { departure, arrival } = await renderLoadedPicker()

    await user.selectOptions(departure, jaffna.id)

    expect(
      within(arrival).getByRole('option', { name: 'Jaffna' }),
    ).toBeDisabled()

    await user.selectOptions(departure, '')

    expect(
      within(arrival).getByRole('option', { name: 'Jaffna' }),
    ).toBeEnabled()

    await user.selectOptions(arrival, trincomalee.id)

    expect(
      within(departure).getByRole('option', { name: 'Trincomalee' }),
    ).toBeDisabled()
  })

  it('recovers from a failed request when Retry is clicked', async () => {
    mockedGetStations.mockRejectedValueOnce(new Error('Network failure'))
    const user = userEvent.setup()

    render(<JourneyStationPicker />)

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Unable to load stations.',
    )
    expect(
      screen.getByRole('combobox', { name: 'Departure station' }),
    ).toBeDisabled()

    await user.click(screen.getByRole('button', { name: 'Retry' }))

    await waitFor(() => {
      expect(
        screen.getByRole('combobox', { name: 'Departure station' }),
      ).toBeEnabled()
    })

    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    expect(mockedGetStations).toHaveBeenCalledTimes(2)
  })

  it('explains an empty station list and keeps selectors disabled', async () => {
    mockedGetStations.mockResolvedValueOnce([])

    render(<JourneyStationPicker />)

    await waitFor(() => {
      expect(screen.getByRole('status')).toHaveTextContent(
        'No stations are currently available.',
      )
    })

    expect(
      screen.getByRole('combobox', { name: 'Departure station' }),
    ).toBeDisabled()
    expect(
      screen.getByRole('combobox', { name: 'Arrival station' }),
    ).toBeDisabled()
    expect(
      screen.queryByRole('button', { name: 'Retry' }),
    ).not.toBeInTheDocument()
  })
})
