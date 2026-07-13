import { resolveHttpUrl, getApiKey, isNexusForgeEnvelope } from './config'

export class HttpError extends Error {
  status: number
  statusText: string
  body: unknown

  constructor(response: Response, body: unknown) {
    // NexusForge：从后端信封 {code, message, data} 提取 message，附加到默认 HTTP 错误描述后
    let serverMessage = ''
    if (body && typeof body === 'object' && 'message' in body) {
      const msg = (body as { message?: unknown }).message
      if (typeof msg === 'string' && msg.length > 0) serverMessage = msg
    }
    const prefix = `HTTP ${response.status} ${response.statusText}`.trim()
    super(serverMessage ? `${prefix}: ${serverMessage}` : prefix)
    this.name = 'HttpError'
    this.status = response.status
    this.statusText = response.statusText
    this.body = body
  }
}

export interface FetchJsonOptions extends Omit<RequestInit, 'body'> {
  body?: unknown
  timeoutMs?: number
}

function mergeHeaders(headers?: HeadersInit, hasBody = false): Headers {
  const merged = new Headers(headers)
  if (hasBody && !merged.has('Content-Type')) {
    merged.set('Content-Type', 'application/json')
  }
  return merged
}

function composeAbortSignal(signal?: AbortSignal | null, timeoutMs?: number): {
  signal?: AbortSignal
  cleanup: () => void
} {
  if (!timeoutMs) {
    return { signal: signal ?? undefined, cleanup: () => {} }
  }
  const controller = new AbortController()
  const abort = () => controller.abort()
  const timer = window.setTimeout(abort, timeoutMs)

  if (signal?.aborted) {
    abort()
  } else {
    signal?.addEventListener('abort', abort, { once: true })
  }

  return {
    signal: controller.signal,
    cleanup: () => {
      window.clearTimeout(timer)
      signal?.removeEventListener('abort', abort)
    },
  }
}

async function readResponseBody(response: Response): Promise<unknown> {
  if (response.status === 204) return undefined
  const text = await response.text()
  if (!text.trim()) return undefined
  try {
    return JSON.parse(text)
  } catch {
    return text
  }
}

export async function fetchJson<T>(absolutePathFromRoot: string, options: FetchJsonOptions = {}): Promise<T> {
  const { body, timeoutMs, signal, headers, ...rest } = options
  const hasBody = body !== undefined
  const abort = composeAbortSignal(signal, timeoutMs)
  // NexusForge：注入 X-API-Key 鉴权头
  const finalHeaders = mergeHeaders(headers, hasBody)
  const apiKey = getApiKey()
  if (apiKey) {
    finalHeaders.set('X-API-Key', apiKey)
  }
  try {
    const response = await fetch(resolveHttpUrl(absolutePathFromRoot), {
      ...rest,
      signal: abort.signal,
      headers: finalHeaders,
      body: hasBody ? JSON.stringify(body) : undefined,
    })
    const data = await readResponseBody(response)
    if (!response.ok) {
      throw new HttpError(response, data)
    }
    // NexusForge：解包 {code, message, data} 信封，返回 data 字段
    if (isNexusForgeEnvelope(data)) {
      return data.data as T
    }
    return data as T
  } finally {
    abort.cleanup()
  }
}

export async function fetchOk(absolutePathFromRoot: string, options: FetchJsonOptions = {}): Promise<Response> {
  const { timeoutMs, signal, body, headers, ...rest } = options
  const hasBody = body !== undefined
  const abort = composeAbortSignal(signal, timeoutMs)
  // NexusForge：注入 X-API-Key 鉴权头（fetchOk 不解包信封，调用方自行处理 Response）
  const finalHeaders = mergeHeaders(headers, hasBody)
  const apiKey = getApiKey()
  if (apiKey) {
    finalHeaders.set('X-API-Key', apiKey)
  }
  try {
    const response = await fetch(resolveHttpUrl(absolutePathFromRoot), {
      ...rest,
      signal: abort.signal,
      headers: finalHeaders,
      body: hasBody ? JSON.stringify(body) : undefined,
    })
    if (!response.ok) {
      throw new HttpError(response, await readResponseBody(response))
    }
    return response
  } finally {
    abort.cleanup()
  }
}

export function fetchUrl(absolutePathFromRoot: string): string {
  return resolveHttpUrl(absolutePathFromRoot)
}
