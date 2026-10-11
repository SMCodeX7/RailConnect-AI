import { getJson } from '../../shared/api/http'
import type { Station, StationListResponse } from './types'

export async function getStations(signal: AbortSignal): Promise<Station[]> {
  const stations: Station[] = []
  let offset = 0

  while (true) {
    const page = await getJson<StationListResponse>(
      `/api/v1/stations?limit=100&offset=${offset}`,
      signal,
    )

    stations.push(...page.items)
    offset += page.items.length

    if (offset >= page.total) {
      return stations
    }

    if (page.items.length === 0) {
      throw new Error('Station pagination returned an incomplete response.')
    }
  }
}
