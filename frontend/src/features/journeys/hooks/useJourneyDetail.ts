import { useEffect, useRef, useState } from 'react'

import { getJourneyDetail } from '../api'
import type { Journey, JourneyDetailResponse } from '../types'

export interface JourneyDetailState {
  status: 'idle' | 'loading' | 'ready' | 'error'
  result: JourneyDetailResponse | null
}

export function useJourneyDetail() {
  const controllerRef = useRef<AbortController | null>(null)
  const targetRef = useRef<Journey | null>(null)
  const [state, setState] = useState<JourneyDetailState>({
    status: 'idle',
    result: null,
  })

  useEffect(() => {
    return () => controllerRef.current?.abort()
  }, [])

  function reset() {
    controllerRef.current?.abort()
    controllerRef.current = null
    targetRef.current = null
    setState({ status: 'idle', result: null })
  }

  async function load(journey: Journey): Promise<void> {
    controllerRef.current?.abort()
    targetRef.current = journey

    const controller = new AbortController()
    controllerRef.current = controller
    setState({ status: 'loading', result: null })

    try {
      const result = await getJourneyDetail(
        {
          runId: journey.run_id,
          departureStopSequence: journey.departure_stop_sequence,
          arrivalStopSequence: journey.arrival_stop_sequence,
        },
        controller.signal,
      )

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

  function retry() {
    if (targetRef.current) {
      void load(targetRef.current)
    }
  }

  return { ...state, load, retry, reset }
}
