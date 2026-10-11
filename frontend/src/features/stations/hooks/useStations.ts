import { useEffect, useState } from 'react'

import { getStations } from '../api'
import type { Station } from '../types'

interface StationState {
  stations: Station[]
  status: 'loading' | 'ready' | 'error'
}

export function useStations() {
  const [attempt, setAttempt] = useState(0)
  const [state, setState] = useState<StationState>({
    stations: [],
    status: 'loading',
  })

  useEffect(() => {
    const controller = new AbortController()

    getStations(controller.signal)
      .then((stations) => {
        if (!controller.signal.aborted) {
          setState({ stations, status: 'ready' })
        }
      })
      .catch(() => {
        if (!controller.signal.aborted) {
          setState({ stations: [], status: 'error' })
        }
      })

    return () => controller.abort()
  }, [attempt])

  function retry() {
    setState({ stations: [], status: 'loading' })
    setAttempt((previous) => previous + 1)
  }

  return { ...state, retry }
}
