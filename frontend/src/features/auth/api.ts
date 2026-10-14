import { getJson, postEmpty, postJson } from '../../shared/api/http'
import type { StaffLoginInput, StaffSession } from './types'

export function loginStaff(
  input: StaffLoginInput,
  signal: AbortSignal,
): Promise<StaffSession> {
  return postJson<StaffSession>('/api/v1/auth/login', input, signal)
}

export function restoreStaffSession(
  signal: AbortSignal,
): Promise<StaffSession> {
  return getJson<StaffSession>('/api/v1/auth/me', signal)
}

export function logoutStaff(
  csrfToken: string,
  signal: AbortSignal,
): Promise<void> {
  return postEmpty('/api/v1/auth/logout', signal, csrfToken)
}
