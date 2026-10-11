import { useEffect, useRef, useState } from 'react'

import { getJourneys } from '../api'
import type { JourneyListResponse, JourneySearchInput } from '../types'

interface JourneyState {
  status: 'idle' | 'loading' | 'ready' | 'error'
  result: JourneyListResponse | null
}

export function useJourneys() {
  const controllerRef = useRef<AbortController | null>(null)
  const [state, setState] = useState<JourneyState>({
    status: 'idle',
    result: null,
  })

  useEffect(() => {
    return () => {
      controllerRef.current?.abort()
    }
  }, [])

  function reset() {
    controllerRef.current?.abort()
    controllerRef.current = null
    setState({ status: 'idle', result: null })
  }

  async function search(input: JourneySearchInput): Promise<void> {
    controllerRef.current?.abort()

    const controller = new AbortController()
    controllerRef.current = controller
    setState({ status: 'loading', result: null })

    try {
      const result = await getJourneys(input, controller.signal)

      if (
        !controller.signal.aborted &&
        controllerRef.current === controller
      ) {
        setState({ status: 'ready', result })
      }
    } catch {
      if (
        !controller.signal.aborted &&
        controllerRef.current === controller
      ) {
        setState({ status: 'error', result: null })
      }
    } finally {
      if (controllerRef.current === controller) {
        controllerRef.current = null
      }
    }
  }

  return { ...state, search, reset }
}
