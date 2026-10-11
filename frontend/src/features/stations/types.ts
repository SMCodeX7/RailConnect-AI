export interface Station {
  id: string
  code: string
  name: string
  source_ref: string
  is_active: boolean
}

export interface StationListResponse {
  items: Station[]
  total: number
  limit: number
  offset: number
}
