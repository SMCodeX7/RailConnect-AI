import { beforeEach, describe, expect, it, vi } from 'vitest'

import { getJson, postEmpty, postJson } from '../../shared/api/http'
import { loginStaff, logoutStaff, restoreStaffSession } from './api'
import type { StaffSession } from './types'

vi.mock('../../shared/api/http', () => ({
  getJson: vi.fn(),
  postJson: vi.fn(),
  postEmpty: vi.fn(),
}))

const session: StaffSession = {
  actor: {
    user_id: 'staff-test-id',
    username: 'local_controller',
    display_name: 'Local Controller',
    roles: ['controller'],
    permissions: ['reports.read', 'reports.review'],
  },
  csrf_token: 'test-csrf-token',
  expires_at: '2030-01-01T00:00:00Z',
}

describe('Staff authentication API', () => {
  beforeEach(() => {
    vi.resetAllMocks()
  })

  it('sends credentials to the login endpoint', async () => {
    vi.mocked(postJson).mockResolvedValue(session)

    const signal = new AbortController().signal
    const input = {
      username: 'local_controller',
      password: 'private-test-password',
    }

    await expect(loginStaff(input, signal)).resolves.toEqual(session)

    expect(postJson).toHaveBeenCalledWith(
      '/api/v1/auth/login',
      input,
      signal,
    )
  })

  it('restores the current session', async () => {
    vi.mocked(getJson).mockResolvedValue(session)

    const signal = new AbortController().signal

    await expect(restoreStaffSession(signal)).resolves.toEqual(session)

    expect(getJson).toHaveBeenCalledWith('/api/v1/auth/me', signal)
  })

  it('sends the CSRF token when signing out', async () => {
    vi.mocked(postEmpty).mockResolvedValue(undefined)

    const signal = new AbortController().signal

    await expect(
      logoutStaff('test-csrf-token', signal),
    ).resolves.toBeUndefined()

    expect(postEmpty).toHaveBeenCalledWith(
      '/api/v1/auth/logout',
      signal,
      'test-csrf-token',
    )
  })
})
