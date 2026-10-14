import { cleanup, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'

import App from './App'

vi.mock('./features/journeys/components/JourneyStationPicker', () => ({
  JourneyStationPicker: () => (
    <section aria-label="Journey search interface">
      Journey search interface
    </section>
  ),
}))

vi.mock('./features/auth/components/StaffPanel', () => ({
  StaffPanel: () => (
    <section aria-label="Staff access interface">
      Staff access interface
    </section>
  ),
}))

describe('Application navigation', () => {
  afterEach(() => {
    cleanup()
  })

  it('opens journey search by default', () => {
    render(<App />)

    expect(
      screen.getByRole('region', { name: 'Journey search interface' }),
    ).toBeInTheDocument()

    expect(
      screen.queryByRole('region', { name: 'Staff access interface' }),
    ).not.toBeInTheDocument()

    expect(
      screen.getByRole('button', { name: 'Journey search' }),
    ).toHaveAttribute('aria-pressed', 'true')

    expect(
      screen.getByRole('button', { name: 'Staff access' }),
    ).toHaveAttribute('aria-pressed', 'false')
  })

  it('opens staff access and updates the selected navigation button', async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getByRole('button', { name: 'Staff access' }))

    expect(
      screen.getByRole('region', { name: 'Staff access interface' }),
    ).toBeInTheDocument()

    expect(
      screen.queryByRole('region', { name: 'Journey search interface' }),
    ).not.toBeInTheDocument()

    expect(
      screen.getByRole('button', { name: 'Staff access' }),
    ).toHaveAttribute('aria-pressed', 'true')

    expect(
      screen.getByRole('button', { name: 'Journey search' }),
    ).toHaveAttribute('aria-pressed', 'false')
  })

  it('returns to public journey search from staff access', async () => {
    const user = userEvent.setup()
    render(<App />)

    await user.click(screen.getByRole('button', { name: 'Staff access' }))
    await user.click(screen.getByRole('button', { name: 'Journey search' }))

    expect(
      screen.getByRole('region', { name: 'Journey search interface' }),
    ).toBeInTheDocument()

    expect(
      screen.queryByRole('region', { name: 'Staff access interface' }),
    ).not.toBeInTheDocument()

    expect(
      screen.getByRole('button', { name: 'Journey search' }),
    ).toHaveAttribute('aria-pressed', 'true')
  })
})
