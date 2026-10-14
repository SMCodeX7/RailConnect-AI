import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import { ApiError, getJson, postEmpty, postJson } from './http'

const fetchMock = vi.fn<typeof fetch>()

function requestOptions(): RequestInit {
  const options = fetchMock.mock.calls[0]?.[1]

  if (!options) {
    throw new Error('Expected a fetch request.')
  }

  return options
}

describe('Shared HTTP client', () => {
  beforeEach(() => {
    fetchMock.mockReset()
    vi.stubGlobal('fetch', fetchMock)
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('reads JSON with same-origin cookies and caching disabled', async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ status: 'ready' }), {
        headers: { 'Content-Type': 'application/json' },
      }),
    )

    const result = await getJson<{ status: string }>(
      '/api/v1/example',
      new AbortController().signal,
    )

    expect(result).toEqual({ status: 'ready' })
    expect(fetchMock.mock.calls[0][0]).toBe('/api/v1/example')

    const options = requestOptions()

    expect(options.credentials).toBe('same-origin')
    expect(options.cache).toBe('no-store')
    expect(new Headers(options.headers).get('Accept')).toBe('application/json')
  })

  it('posts JSON without adding a CSRF token to login', async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ accepted: true })),
    )

    await postJson(
      '/api/v1/auth/login',
      { username: 'staff', password: 'private-test-password' },
      new AbortController().signal,
    )

    const options = requestOptions()
    const headers = new Headers(options.headers)

    expect(options.method).toBe('POST')
    expect(headers.get('Content-Type')).toBe('application/json')
    expect(headers.has('X-CSRF-Token')).toBe(false)
    expect(JSON.parse(options.body as string)).toEqual({
      username: 'staff',
      password: 'private-test-password',
    })
  })

  it('includes a supplied CSRF token in a JSON mutation', async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify({ saved: true })))

    await postJson(
      '/api/v1/example',
      { value: 'test' },
      new AbortController().signal,
      'test-csrf-token',
    )

    expect(
      new Headers(requestOptions().headers).get('X-CSRF-Token'),
    ).toBe('test-csrf-token')
  })

  it('handles an empty logout response without parsing JSON', async () => {
    const response = new Response(null, { status: 204 })
    const jsonSpy = vi.spyOn(response, 'json')

    fetchMock.mockResolvedValue(response)

    await expect(
      postEmpty(
        '/api/v1/auth/logout',
        new AbortController().signal,
        'test-csrf-token',
      ),
    ).resolves.toBeUndefined()

    const options = requestOptions()

    expect(options.method).toBe('POST')
    expect(new Headers(options.headers).get('X-CSRF-Token')).toBe(
      'test-csrf-token',
    )
    expect(options.body).toBe('{}')
    expect(jsonSpy).not.toHaveBeenCalled()
  })

  it('preserves structured errors and response correlation headers', async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          code: 'RATE_LIMITED',
          message: 'Too many requests.',
          request_id: 'test-request-id',
        }),
        {
          status: 429,
          headers: {
            'Content-Type': 'application/json',
            'X-Request-ID': 'test-request-id',
            'Retry-After': '12.5',
          },
        },
      ),
    )

    await expect(
      getJson('/api/v1/example', new AbortController().signal),
    ).rejects.toMatchObject({
      name: 'ApiError',
      status: 429,
      code: 'RATE_LIMITED',
      message: 'Too many requests.',
      requestId: 'test-request-id',
      retryAfter: 13,
    })
  })

  it('uses a safe fallback for non-JSON errors', async () => {
    fetchMock.mockResolvedValue(
      new Response('<html>Service unavailable</html>', {
        status: 503,
        headers: { 'Retry-After': 'invalid' },
      }),
    )

    await expect(
      getJson('/api/v1/example', new AbortController().signal),
    ).rejects.toMatchObject({
      name: 'ApiError',
      status: 503,
      code: 'HTTP_ERROR',
      message: 'Request failed with status 503.',
      requestId: null,
      retryAfter: null,
    })
  })

  it('rejects invalid error fields and negative retry intervals', async () => {
    fetchMock.mockResolvedValue(
      new Response(
        JSON.stringify({
          code: 'invalid code!',
          message: 'x'.repeat(501),
        }),
        {
          status: 400,
          headers: { 'Retry-After': '-1' },
        },
      ),
    )

    await expect(
      getJson('/api/v1/example', new AbortController().signal),
    ).rejects.toMatchObject({
      code: 'HTTP_ERROR',
      message: 'Request failed with status 400.',
      retryAfter: null,
    })
  })

  it('creates actual ApiError instances', async () => {
    fetchMock.mockResolvedValue(
      new Response(JSON.stringify({ code: 'FORBIDDEN' }), { status: 403 }),
    )

    await expect(
      getJson('/api/v1/example', new AbortController().signal),
    ).rejects.toBeInstanceOf(ApiError)
  })

  it('rejects paths outside the local API before fetching', async () => {
    await expect(
      getJson('https://example.com/auth', new AbortController().signal),
    ).rejects.toThrow('API requests require a local /api/ path.')

    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('propagates caller cancellation to the request signal', async () => {
    fetchMock.mockResolvedValue(new Response(JSON.stringify({})))

    const controller = new AbortController()

    await getJson('/api/v1/example', controller.signal)

    const signal = requestOptions().signal

    expect(signal).toBeDefined()
    expect(signal?.aborted).toBe(false)

    controller.abort()

    expect(signal?.aborted).toBe(true)
  })

  it('combines caller cancellation with a ten-second timeout', async () => {
    const timeoutController = new AbortController()
    const timeoutSpy = vi
      .spyOn(AbortSignal, 'timeout')
      .mockReturnValue(timeoutController.signal)

    fetchMock.mockResolvedValue(new Response(JSON.stringify({})))

    await getJson('/api/v1/example', new AbortController().signal)

    expect(timeoutSpy).toHaveBeenCalledWith(10000)

    timeoutController.abort()

    expect(requestOptions().signal?.aborted).toBe(true)
  })
})
