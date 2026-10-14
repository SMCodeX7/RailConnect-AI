import { useCallback, useEffect, useRef, useState } from 'react'

import { ApiError } from '../../../shared/api/http'
import { loginStaff, logoutStaff, restoreStaffSession } from '../api'
import type {
  StaffLoginInput,
  StaffPermission,
  StaffSession,
} from '../types'

interface StaffSessionState {
  status: 'checking' | 'guest' | 'authenticated' | 'unavailable'
  session: StaffSession | null
  busy: boolean
  error: string | null
}

function loginErrorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 401) {
      return 'The username or password is incorrect, or the account is unavailable.'
    }

    if (error.status === 429) {
      return error.retryAfter !== null
        ? `Too many sign-in attempts. Try again in ${error.retryAfter} seconds.`
        : 'Too many sign-in attempts. Please try again later.'
    }

    if (error.status === 403) {
      return 'Sign-in was denied. Check that you are using the correct application address.'
    }
  }

  return 'Unable to sign in. Please try again.'
}

export function useStaffSession() {
  const controllerRef = useRef<AbortController | null>(null)
  const [state, setState] = useState<StaffSessionState>({
    status: 'checking',
    session: null,
    busy: false,
    error: null,
  })

  const restore = useCallback(async (controller: AbortController) => {
    try {
      const session = await restoreStaffSession(controller.signal)

      if (
        !controller.signal.aborted &&
        controllerRef.current === controller
      ) {
        setState({
          status: 'authenticated',
          session,
          busy: false,
          error: null,
        })
      }
    } catch (error) {
      if (
        !controller.signal.aborted &&
        controllerRef.current === controller
      ) {
        const guest = error instanceof ApiError && error.status === 401

        setState({
          status: guest ? 'guest' : 'unavailable',
          session: null,
          busy: false,
          error: guest ? null : 'Unable to check your staff session.',
        })
      }
    }
  }, [])

  useEffect(() => {
    const controller = new AbortController()
    controllerRef.current = controller

    queueMicrotask(() => {
      if (!controller.signal.aborted) {
        void restore(controller)
      }
    })

    return () => {
      controller.abort()
      controllerRef.current?.abort()
    }
  }, [restore])

  useEffect(() => {
    if (state.status !== 'authenticated' || !state.session) return

    const remaining = Date.parse(state.session.expires_at) - Date.now()

    const timer = window.setTimeout(() => {
      controllerRef.current?.abort()
      controllerRef.current = null

      setState({
        status: 'guest',
        session: null,
        busy: false,
        error: 'Your session has expired. Please sign in again.',
      })
    }, Math.max(0, remaining))

    return () => window.clearTimeout(timer)
  }, [state.status, state.session])

  function refresh() {
    controllerRef.current?.abort()

    const controller = new AbortController()
    controllerRef.current = controller

    setState({
      status: 'checking',
      session: null,
      busy: false,
      error: null,
    })

    void restore(controller)
  }

  async function signIn(input: StaffLoginInput): Promise<void> {
    if (state.busy) return

    controllerRef.current?.abort()

    const controller = new AbortController()
    controllerRef.current = controller

    setState({
      status: 'guest',
      session: null,
      busy: true,
      error: null,
    })

    try {
      const session = await loginStaff(input, controller.signal)

      if (
        !controller.signal.aborted &&
        controllerRef.current === controller
      ) {
        setState({
          status: 'authenticated',
          session,
          busy: false,
          error: null,
        })
      }
    } catch (error) {
      if (
        !controller.signal.aborted &&
        controllerRef.current === controller
      ) {
        setState({
          status: 'guest',
          session: null,
          busy: false,
          error: loginErrorMessage(error),
        })
      }
    }
  }

  async function signOut(): Promise<void> {
    if (!state.session || state.busy) return

    const previousSession = state.session
    controllerRef.current?.abort()

    const controller = new AbortController()
    controllerRef.current = controller

    setState((previous) => ({
      ...previous,
      busy: true,
      error: null,
    }))

    try {
      await logoutStaff(previousSession.csrf_token, controller.signal)

      if (
        !controller.signal.aborted &&
        controllerRef.current === controller
      ) {
        setState({
          status: 'guest',
          session: null,
          busy: false,
          error: null,
        })
      }
    } catch (error) {
      if (
        !controller.signal.aborted &&
        controllerRef.current === controller
      ) {
        const expired = error instanceof ApiError && error.status === 401

        setState({
          status: expired ? 'guest' : 'authenticated',
          session: expired ? null : previousSession,
          busy: false,
          error: expired
            ? 'Your session has expired. Please sign in again.'
            : 'Sign-out could not be confirmed. Refresh your session and try again.',
        })
      }
    }
  }

  function hasPermission(permission: StaffPermission): boolean {
    return (
      state.status === 'authenticated' &&
      Boolean(state.session?.actor.permissions.includes(permission))
    )
  }

  return {
    ...state,
    signIn,
    signOut,
    refresh,
    hasPermission,
  }
}
