import { act, cleanup, render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError } from '../../../shared/api/http'
import { loginStaff, logoutStaff, restoreStaffSession } from '../api'
import type { StaffSession } from '../types'
import { StaffPanel } from './StaffPanel'

vi.mock('../api', () => ({
  loginStaff: vi.fn(),
  logoutStaff: vi.fn(),
  restoreStaffSession: vi.fn(),
}))

const loginMock = vi.mocked(loginStaff)
const logoutMock = vi.mocked(logoutStaff)
const restoreMock = vi.mocked(restoreStaffSession)

function sessionFixture(): StaffSession {
  return {
    actor: {
      user_id: 'staff-test-id',
      username: 'local_controller',
      display_name: 'Local Controller',
      roles: ['controller'],
      permissions: [
        'reports.read',
        'reports.review',
        'incidents.edit',
        'incidents.resolve',
      ],
    },
    csrf_token: 'test-csrf-token',
    expires_at: new Date(Date.now() + 60 * 60 * 1000).toISOString(),
  }
}

function apiError(status: number, retryAfter: number | null = null): ApiError {
  const error = new Error(`Request failed with status ${status}.`)
  Object.setPrototypeOf(error, ApiError.prototype)

  return Object.assign(error, {
    status,
    code: 'HTTP_ERROR',
    requestId: null,
    retryAfter,
  }) as ApiError
}

async function fillLoginForm() {
  const user = userEvent.setup()

  await screen.findByLabelText('Staff username')
  await user.type(screen.getByLabelText('Staff username'), 'local_controller')
  await user.type(screen.getByLabelText('Password'), 'private-test-password')

  return user
}

describe('Staff panel', () => {
  beforeEach(() => {
    vi.resetAllMocks()
    restoreMock.mockRejectedValue(apiError(401))
    loginMock.mockResolvedValue(sessionFixture())
    logoutMock.mockResolvedValue(undefined)
  })

  afterEach(() => {
    cleanup()
  })

  it('shows checking state while restoring a session', () => {
    restoreMock.mockReturnValue(new Promise<StaffSession>(() => {}))

    render(<StaffPanel />)

    expect(screen.getByRole('status')).toHaveTextContent(
      'Checking your staff session',
    )
    expect(screen.queryByLabelText('Password')).not.toBeInTheDocument()
  })

  it('shows the sign-in form when no session exists', async () => {
    render(<StaffPanel />)

    expect(await screen.findByLabelText('Staff username')).toBeInTheDocument()
    expect(screen.getByLabelText('Password')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Sign in' })).toBeDisabled()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('restores the account and displays its permissions', async () => {
    restoreMock.mockResolvedValue(sessionFixture())

    render(<StaffPanel />)

    expect(await screen.findByText('Local Controller')).toBeInTheDocument()
    expect(screen.getByText('Controller', { exact: true })).toBeInTheDocument()
    expect(screen.getByText('Review passenger reports')).toBeInTheDocument()
    expect(screen.getByText('Resolve verified incidents')).toBeInTheDocument()
    expect(screen.queryByText('Manage timetable imports')).not.toBeInTheDocument()
    expect(screen.queryByText('View audit history')).not.toBeInTheDocument()
    expect(screen.queryByText('test-csrf-token')).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Password')).not.toBeInTheDocument()
  })

  it('recovers from a failed session check', async () => {
    const user = userEvent.setup()
    restoreMock.mockRejectedValueOnce(new Error('Network unavailable'))

    render(<StaffPanel />)

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Unable to check your staff session',
    )

    restoreMock.mockResolvedValueOnce(sessionFixture())
    await user.click(screen.getByRole('button', { name: 'Retry session check' }))

    expect(await screen.findByText('Local Controller')).toBeInTheDocument()
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('signs in and clears the password while the request is pending', async () => {
    let resolveLogin!: (session: StaffSession) => void

    loginMock.mockReturnValue(
      new Promise<StaffSession>((resolve) => {
        resolveLogin = resolve
      }),
    )

    render(<StaffPanel />)

    const user = await fillLoginForm()
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(screen.getByLabelText('Password')).toHaveValue('')
    expect(screen.getByRole('button', { name: 'Signing in…' })).toBeDisabled()

    expect(loginMock).toHaveBeenCalledWith(
      {
        username: 'local_controller',
        password: 'private-test-password',
      },
      expect.any(AbortSignal),
    )

    await act(async () => {
      resolveLogin(sessionFixture())
    })

    expect(await screen.findByText('Local Controller')).toBeInTheDocument()
    expect(screen.queryByLabelText('Password')).not.toBeInTheDocument()
  })

  it('shows a generic message for rejected credentials', async () => {
    loginMock.mockRejectedValue(apiError(401))

    render(<StaffPanel />)

    const user = await fillLoginForm()
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'The username or password is incorrect, or the account is unavailable.',
    )
    expect(screen.getByLabelText('Password')).toHaveValue('')
    expect(screen.queryByText('Local Controller')).not.toBeInTheDocument()
  })

  it('displays the server retry interval after rate limiting', async () => {
    loginMock.mockRejectedValue(apiError(429, 60))

    render(<StaffPanel />)

    const user = await fillLoginForm()
    await user.click(screen.getByRole('button', { name: 'Sign in' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Too many sign-in attempts. Try again in 60 seconds.',
    )
  })

  it('signs out using the current session CSRF token', async () => {
    const user = userEvent.setup()
    restoreMock.mockResolvedValue(sessionFixture())

    render(<StaffPanel />)

    await screen.findByText('Local Controller')
    await user.click(screen.getByRole('button', { name: 'Sign out' }))

    expect(await screen.findByLabelText('Staff username')).toBeInTheDocument()
    expect(logoutMock).toHaveBeenCalledWith(
      'test-csrf-token',
      expect.any(AbortSignal),
    )
    expect(screen.queryByText('Local Controller')).not.toBeInTheDocument()
  })

  it('retains the account when sign-out cannot be confirmed', async () => {
    const user = userEvent.setup()
    restoreMock.mockResolvedValue(sessionFixture())
    logoutMock.mockRejectedValue(new Error('Network unavailable'))

    render(<StaffPanel />)

    await screen.findByText('Local Controller')
    await user.click(screen.getByRole('button', { name: 'Sign out' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Sign-out could not be confirmed',
    )
    expect(screen.getByText('Local Controller')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Refresh session' })).toBeEnabled()
  })

  it('returns to sign-in when the server rejects an expired session', async () => {
    const user = userEvent.setup()
    restoreMock.mockResolvedValue(sessionFixture())
    logoutMock.mockRejectedValue(apiError(401))

    render(<StaffPanel />)

    await screen.findByText('Local Controller')
    await user.click(screen.getByRole('button', { name: 'Sign out' }))

    expect(await screen.findByLabelText('Staff username')).toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent(
      'Your session has expired',
    )
    expect(screen.queryByText('Local Controller')).not.toBeInTheDocument()
  })

  it('clears an account whose absolute expiry has passed', async () => {
    restoreMock.mockResolvedValue({
      ...sessionFixture(),
      expires_at: new Date(Date.now() - 1000).toISOString(),
    })

    render(<StaffPanel />)

    expect(await screen.findByLabelText('Staff username')).toBeInTheDocument()
    expect(screen.getByRole('alert')).toHaveTextContent(
      'Your session has expired',
    )
    expect(screen.queryByText('Local Controller')).not.toBeInTheDocument()
  })

  it('aborts session restoration when the panel unmounts', async () => {
    restoreMock.mockReturnValue(new Promise<StaffSession>(() => {}))

    const { unmount } = render(<StaffPanel />)

    await waitFor(() => {
      expect(restoreMock).toHaveBeenCalledTimes(1)
    })

    const signal = restoreMock.mock.calls[0][0]
    expect(signal.aborted).toBe(false)

    unmount()

    expect(signal.aborted).toBe(true)
  })
})
