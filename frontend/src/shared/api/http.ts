export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly requestId: string | null
  readonly retryAfter: number | null

  constructor(
    message: string,
    status: number,
    code: string,
    requestId: string | null,
    retryAfter: number | null,
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.requestId = requestId
    this.retryAfter = retryAfter
  }
}

async function readApiError(response: Response): Promise<ApiError> {
  let payload: unknown

  try {
    payload = await response.json()
  } catch {
    payload = null
  }

  let message = `Request failed with status ${response.status}.`
  let code = 'HTTP_ERROR'

  if (typeof payload === 'object' && payload !== null) {
    if (
      'message' in payload &&
      typeof payload.message === 'string' &&
      payload.message.length <= 500
    ) {
      message = payload.message
    }

    if (
      'code' in payload &&
      typeof payload.code === 'string' &&
      /^[A-Z0-9_]{1,64}$/.test(payload.code)
    ) {
      code = payload.code
    }
  }

  const retryHeader = response.headers.get('Retry-After')
  const retryValue = retryHeader === null ? NaN : Number(retryHeader)
  const retryAfter =
    Number.isFinite(retryValue) && retryValue >= 0
      ? Math.ceil(retryValue)
      : null

  return new ApiError(
    message,
    response.status,
    code,
    response.headers.get('X-Request-ID'),
    retryAfter,
  )
}

async function request(
  path: string,
  signal: AbortSignal,
  options: RequestInit = {},
): Promise<Response> {
  if (!path.startsWith('/api/')) {
    throw new Error('API requests require a local /api/ path.')
  }

  const headers = new Headers(options.headers)
  headers.set('Accept', 'application/json')

  const response = await fetch(path, {
    ...options,
    headers,
    credentials: 'same-origin',
    cache: 'no-store',
    signal: AbortSignal.any([
      signal,
      AbortSignal.timeout(10000),
    ]),
  })

  if (!response.ok) {
    throw await readApiError(response)
  }

  return response
}

export async function getJson<T>(
  path: string,
  signal: AbortSignal,
): Promise<T> {
  const response = await request(path, signal)
  return (await response.json()) as T
}

export async function postJson<T>(
  path: string,
  body: unknown,
  signal: AbortSignal,
  csrfToken?: string,
): Promise<T> {
  const headers = new Headers({ 'Content-Type': 'application/json' })
  if (csrfToken) {
    headers.set('X-CSRF-Token', csrfToken)
  }

  const response = await request(path, signal, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
  })

  return (await response.json()) as T
}

export async function postEmpty(
  path: string,
  signal: AbortSignal,
  csrfToken: string,
): Promise<void> {
  await request(path, signal, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRF-Token': csrfToken,
    },
    body: JSON.stringify({}),
  })
}
