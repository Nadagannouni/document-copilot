import { env } from '@/lib/env'
import { getAccessToken } from '@/lib/supabase'

const DEFAULT_TIMEOUT_MS = 20_000

export type ApiErrorDetails = {
  status: number | null
  message: string
  code?: string
  details?: unknown
  isNetworkError: boolean
}

export class ApiError extends Error {
  readonly status: number | null
  readonly code?: string
  readonly details?: unknown
  readonly isNetworkError: boolean

  constructor(details: ApiErrorDetails) {
    super(details.message)
    this.name = 'ApiError'
    this.status = details.status
    this.code = details.code
    this.details = details.details
    this.isNetworkError = details.isNetworkError
  }
}

type RequestOptions = {
  body?: unknown
  headers?: HeadersInit
  method?: string
  signal?: AbortSignal
  timeoutMs?: number
}

type ErrorPayload = {
  code?: string
  detail?: unknown
  details?: unknown
  error?: unknown
  message?: unknown
}

function buildUrl(path: string): string {
  if (/^https?:\/\//.test(path)) {
    return path
  }

  return `${env.apiBaseUrl}/${path.replace(/^\/+/, '')}`
}

function mergeSignals(signal: AbortSignal | undefined, timeoutMs: number): AbortSignal {
  const timeoutSignal = AbortSignal.timeout(timeoutMs)

  if (!signal) {
    return timeoutSignal
  }

  return AbortSignal.any([signal, timeoutSignal])
}

function isJsonResponse(response: Response): boolean {
  return response.headers.get('content-type')?.includes('application/json') ?? false
}

async function parseResponseBody(response: Response): Promise<unknown> {
  if (response.status === 204) {
    return undefined
  }

  if (isJsonResponse(response)) {
    return response.json()
  }

  const text = await response.text()
  return text === '' ? undefined : text
}

function getErrorMessage(payload: unknown, fallback: string): string {
  if (!payload || typeof payload !== 'object') {
    return fallback
  }

  const errorPayload = payload as ErrorPayload

  if (typeof errorPayload.message === 'string') {
    return errorPayload.message
  }

  if (typeof errorPayload.detail === 'string') {
    return errorPayload.detail
  }

  if (typeof errorPayload.error === 'string') {
    return errorPayload.error
  }

  return fallback
}

function getErrorCode(payload: unknown): string | undefined {
  if (!payload || typeof payload !== 'object') {
    return undefined
  }

  const code = (payload as ErrorPayload).code
  return typeof code === 'string' ? code : undefined
}

function getErrorDetails(payload: unknown): unknown {
  if (!payload || typeof payload !== 'object') {
    return payload
  }

  const errorPayload = payload as ErrorPayload
  return errorPayload.details ?? errorPayload.detail ?? errorPayload.error ?? payload
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const token = await getAccessToken()
  const headers = new Headers(options.headers)

  headers.set('Accept', 'application/json')

  let body: BodyInit | undefined
  if (options.body !== undefined) {
    headers.set('Content-Type', 'application/json')
    body = JSON.stringify(options.body)
  }

  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  let response: Response

  try {
    response = await fetch(buildUrl(path), {
      body,
      headers,
      method: options.method ?? 'GET',
      signal: mergeSignals(options.signal, options.timeoutMs ?? DEFAULT_TIMEOUT_MS),
    })
  } catch (error) {
    throw new ApiError({
      status: null,
      message: error instanceof Error ? error.message : 'Network request failed',
      details: error,
      isNetworkError: true,
    })
  }

  const payload = await parseResponseBody(response)

  if (!response.ok) {
    throw new ApiError({
      status: response.status,
      message: getErrorMessage(payload, response.statusText),
      code: getErrorCode(payload),
      details: getErrorDetails(payload),
      isNetworkError: false,
    })
  }

  return payload as T
}

export const http = {
  delete: <T>(path: string, options?: Omit<RequestOptions, 'body' | 'method'>) =>
    request<T>(path, { ...options, method: 'DELETE' }),
  get: <T>(path: string, options?: Omit<RequestOptions, 'body' | 'method'>) =>
    request<T>(path, { ...options, method: 'GET' }),
  patch: <T>(path: string, body?: unknown, options?: Omit<RequestOptions, 'body' | 'method'>) =>
    request<T>(path, { ...options, body, method: 'PATCH' }),
  post: <T>(path: string, body?: unknown, options?: Omit<RequestOptions, 'body' | 'method'>) =>
    request<T>(path, { ...options, body, method: 'POST' }),
  put: <T>(path: string, body?: unknown, options?: Omit<RequestOptions, 'body' | 'method'>) =>
    request<T>(path, { ...options, body, method: 'PUT' }),
}
