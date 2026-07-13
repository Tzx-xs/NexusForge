import axios, { type AxiosError, type AxiosRequestConfig } from 'axios'

import { runtimePerformance } from '../config/performance'
import { emitAxiosFeedbackIncident } from '../support/feedbackNotifier'
import { apiRoutes } from './endpoints'

// ---------------------------------------------------------------------------
// NexusForge 对接适配：X-API-Key 鉴权 + {code,message,data} 信封解包
// ---------------------------------------------------------------------------
// 后端 interfaces/middleware/auth.py 在生产模式下要求 /api/v1/* 携带 X-API-Key。
// 后端统一返回 {code:0, message:"success", data:...} 信封（interfaces/utils/response.py）。
// 业务错误以 HTTP 4xx/5xx + {code, message, data:null} 返回，走 axios error 分支。
const API_KEY_STORAGE_KEY = 'nexusforge_api_key'

/**
 * 读取 API Key：优先 localStorage（运行时设置面板写入），其次 VITE_API_KEY 构建期注入。
 * 开发模式下后端未设置 API_KEY 时本函数返回空字符串，请求不带 X-API-Key 头即可放行。
 */
export function getApiKey(): string {
  if (typeof window !== 'undefined' && window.localStorage) {
    const stored = window.localStorage.getItem(API_KEY_STORAGE_KEY)
    if (stored && stored.length > 0) return stored
  }
  const envKey = (import.meta.env.VITE_API_KEY as string | undefined) ?? ''
  return envKey
}

/**
 * 判断响应体是否为 NexusForge 信封 {code, message, data}。
 * 仅当同时含 code/message/data 三字段且 code 为数字时认定为信封。
 */
export function isNexusForgeEnvelope(body: unknown): body is { code: number; message: string; data: unknown } {
  if (body === null || typeof body !== 'object') return false
  const env = body as Record<string, unknown>
  return (
    typeof env.code === 'number' &&
    typeof env.message === 'string' &&
    'data' in env
  )
}

/**
 * 判断响应体是否为二进制（Blob/ArrayBuffer 等），二进制不应解包信封。
 */
function isBinaryBody(body: unknown): boolean {
  if (typeof Blob !== 'undefined' && body instanceof Blob) return true
  if (typeof ArrayBuffer !== 'undefined' && body instanceof ArrayBuffer) return true
  // axios 在 responseType:'blob' 时返回 Blob，已覆盖；保留 Uint8Array 兜底
  if (typeof Uint8Array !== 'undefined' && body instanceof Uint8Array) return true
  return false
}

// ---------------------------------------------------------------------------
// 单一数据源：axiosInstance.defaults.baseURL
// - 浏览器：`/api/v1`（相对路径，走 Vite 代理）
// - Tauri：`http://127.0.0.1:<port>/api/v1`（initApiClient 内 IPC 写入）
// fetch / EventSource 使用 resolveHttpUrl()，从同一 baseURL 推导 origin。
// Legacy `/api`（非 v1）使用 legacyBookHttp / legacyStatsHttp，由 syncLegacyRootsFromV1 同步主机。
// ---------------------------------------------------------------------------
let _isTauri: boolean | null = null

function isTauri(): boolean {
  if (_isTauri === null) {
    if (typeof window === 'undefined') {
      _isTauri = false
    } else {
      const w = window as Window & {
        __TAURI__?: unknown
        __TAURI_INTERNALS__?: unknown
      }
      _isTauri = !!(w.__TAURI__ || w.__TAURI_INTERNALS__)
    }
  }
  return _isTauri
}

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

const axiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: runtimePerformance.network.apiDefaultTimeoutMs,
  headers: {
    'Content-Type': 'application/json',
  },
})

/** 与 apiClient 同一实例，供需完整 Axios 配置（timeout、params）的模块使用 */
export const apiAxios = axiosInstance

/** 旧版 /api 路由（book、jobs），与 v1 共用主机 */
export const legacyBookHttp = axios.create({
  baseURL: '/api',
  timeout: runtimePerformance.network.legacyApiTimeoutMs,
  headers: {
    'Content-Type': 'application/json',
  },
})
legacyBookHttp.interceptors.response.use(response => response.data)

/** 旧版 /api/stats，带 SuccessResponse 解包 */
export const legacyStatsHttp = axios.create({
  baseURL: '/api',
  timeout: runtimePerformance.network.legacyApiTimeoutMs,
  headers: {
    'Content-Type': 'application/json',
  },
})
legacyStatsHttp.interceptors.response.use(response => {
  const body = response.data
  if (
    body &&
    typeof body === 'object' &&
    'success' in body &&
    (body as { success?: boolean }).success === true &&
    'data' in body
  ) {
    return (body as { data: unknown }).data
  }
  return body
})

function syncLegacyRootsFromV1(): void {
  const v1 = axiosInstance.defaults.baseURL || '/api/v1'
  if (/^https?:\/\//i.test(v1)) {
    const origin = new URL(v1).origin
    legacyBookHttp.defaults.baseURL = `${origin}/api`
    legacyStatsHttp.defaults.baseURL = `${origin}/api`
  } else {
    legacyBookHttp.defaults.baseURL = '/api'
    legacyStatsHttp.defaults.baseURL = '/api'
  }
}

/**
 * 将必须以 `/` 开头的绝对路径（如 `/api/v1/...`）转为实际请求 URL。
 * 与当前 `apiAxios.defaults.baseURL` 一致：浏览器保持相对路径；桌面壳补全 origin。
 */
export function resolveHttpUrl(absolutePathFromRoot: string): string {
  if (!absolutePathFromRoot.startsWith('/')) {
    throw new Error(`resolveHttpUrl: path must start with /, got: ${absolutePathFromRoot}`)
  }
  const v1 = axiosInstance.defaults.baseURL || '/api/v1'
  if (/^https?:\/\//i.test(v1)) {
    return `${new URL(v1).origin}${absolutePathFromRoot}`
  }
  return absolutePathFromRoot
}

async function initTauriConnection(): Promise<void> {
  if (!isTauri()) {
    return
  }
  console.log(`[Tauri] API baseURL: ${axiosInstance.defaults.baseURL}`)
}

/** 桌面壳：后端在后台线程就绪，IPC 端口在健康检查通过前可能为 0 */

async function waitForTauriBackendPort(
  invoke: (cmd: string) => Promise<number>,
  maxWaitMs: number,
  intervalMs: number,
): Promise<number | null> {
  const deadline = Date.now() + maxWaitMs
  while (Date.now() < deadline) {
    const p = await invoke('get_backend_port')
    if (p > 0) {
      return p
    }
    await new Promise<void>(resolve => {
      setTimeout(resolve, intervalMs)
    })
  }
  return null
}

function createTimeoutSignal(timeoutMs: number): { signal: AbortSignal; cleanup: () => void } {
  const abortSignal = AbortSignal as typeof AbortSignal & {
    timeout?: (milliseconds: number) => AbortSignal
  }
  if (typeof abortSignal.timeout === 'function') {
    return { signal: abortSignal.timeout(timeoutMs), cleanup: () => {} }
  }

  const controller = new AbortController()
  const timer = window.setTimeout(() => controller.abort(), timeoutMs)
  return {
    signal: controller.signal,
    cleanup: () => window.clearTimeout(timer),
  }
}

function hasConcreteTauriBackendBaseUrl(): boolean {
  const base = axiosInstance.defaults.baseURL || ''
  return /^https?:\/\/127\.0\.0\.1:\d+\/api\/v1$/i.test(base)
}

async function waitForTauriBackendHealth(port: number, maxWaitMs: number, intervalMs: number): Promise<boolean> {
  const deadline = Date.now() + maxWaitMs
  while (Date.now() < deadline) {
    const healthTimeout = createTimeoutSignal(runtimePerformance.network.tauriHealthCheckTimeoutMs)
    try {
      const healthCheck = await fetch(`http://127.0.0.1:${port}/health`, {
        method: 'GET',
        signal: healthTimeout.signal,
      })
      if (healthCheck.ok) return true
    } catch {
      // Backend may still be binding the socket. Keep polling until the shared deadline.
    } finally {
      healthTimeout.cleanup()
    }
    await new Promise<void>(resolve => {
      setTimeout(resolve, intervalMs)
    })
  }
  return false
}

let tauriBackendReadyPromise: Promise<void> | null = null

async function ensureTauriBackendReady(): Promise<void> {
  if (!isTauri() || hasConcreteTauriBackendBaseUrl()) {
    return
  }
  if (tauriBackendReadyPromise) {
    return tauriBackendReadyPromise
  }

  tauriBackendReadyPromise = (async () => {
    const { invoke } = await import('@tauri-apps/api/core')
    const port = await waitForTauriBackendPort(
      cmd => invoke<number>(cmd),
      runtimePerformance.network.tauriBackendWaitMs,
      runtimePerformance.network.tauriBackendPollMs,
    )
    if (port == null || port <= 0) {
      throw new Error('Tauri 后端端口尚未就绪')
    }
    const healthy = await waitForTauriBackendHealth(
      port,
      runtimePerformance.network.tauriBackendWaitMs,
      runtimePerformance.network.tauriBackendPollMs,
    )
    if (!healthy) {
      throw new Error(`Tauri 后端健康检查未通过: 127.0.0.1:${port}`)
    }
    axiosInstance.defaults.baseURL = `http://127.0.0.1:${port}/api/v1`
    syncLegacyRootsFromV1()
    console.log(`[API] 桌面模式 baseURL: ${axiosInstance.defaults.baseURL}`)
  })()

  try {
    await tauriBackendReadyPromise
  } finally {
    tauriBackendReadyPromise = null
  }
}

/**
 * 初始化 API（应用启动时调用一次）
 */
export async function initApiClient(): Promise<void> {
  let port: number | null = null
  try {
    const { invoke } = await import('@tauri-apps/api/core')
    const first = await invoke<number>('get_backend_port')
    if (first > 0) {
      port = first
    } else if (isTauri()) {
      console.log('[API] 等待后端就绪...')
      port = await waitForTauriBackendPort(
        cmd => invoke<number>(cmd),
        runtimePerformance.network.tauriBackendWaitMs,
        runtimePerformance.network.tauriBackendPollMs,
      )
    }
  } catch (e) {
    console.warn('[API] Tauri IPC 调用失败:', e)
  }

  if (port != null && port > 0) {
    const newBaseURL = `http://127.0.0.1:${port}/api/v1`
    axiosInstance.defaults.baseURL = newBaseURL
    console.log(`[API] 桌面模式 baseURL: ${newBaseURL}`)

    const healthy = await waitForTauriBackendHealth(
      port,
      runtimePerformance.network.tauriBackendWaitMs,
      runtimePerformance.network.tauriBackendPollMs,
    )
    if (!healthy) {
      axiosInstance.defaults.baseURL = API_BASE_URL
      console.warn('[API] 后端健康检查未通过，等待请求门禁继续处理')
    }
  } else if (isTauri()) {
    console.warn('[API] Tauri 下未能通过 IPC 取得端口，等待请求门禁继续处理')
  }

  syncLegacyRootsFromV1()
  await initTauriConnection()
}

function formatAxiosUserSummary(err: AxiosError): string {
  const url = typeof err.config?.url === 'string' ? err.config.url : ''
  const method = err.config?.method ? String(err.config.method).toUpperCase() : ''
  const status = typeof err.response?.status === 'number' ? err.response.status : undefined
  if (typeof status === 'number') {
    return `接口错误 (${status}) ${method} ${url}`.trim()
  }
  if (err.code === 'ECONNABORTED') return `请求超时 ${method} ${url}`.trim()
  const msg = typeof err.message === 'string' ? err.message.trim() : ''
  return msg.length > 0 ? msg : '网络或接口异常'
}

axiosInstance.interceptors.request.use(async config => {
  await ensureTauriBackendReady()
  // NexusForge：注入 X-API-Key 鉴权头（后端 auth_middleware 校验）
  const apiKey = getApiKey()
  if (apiKey) {
    config.headers = config.headers ?? {}
    config.headers['X-API-Key'] = apiKey
  }
  return config
})

axiosInstance.interceptors.response.use(
  response => {
    const body = response.data
    // 二进制响应（导出 Blob 等）不解包
    if (isBinaryBody(body)) {
      return body
    }
    // NexusForge 信封 {code, message, data}：解包返回 data
    // 后端约定 HTTP 200 永远 code=0，故此处不再判断 code != 0
    if (isNexusForgeEnvelope(body)) {
      return body.data
    }
    // 非信封响应（如旧版 /api、第三方代理）原样返回
    return body
  },
  err => {
    const axErr = err as AxiosError
    const cfg = axErr.config as (AxiosRequestConfig & { silentGlobalFeedback?: boolean }) | undefined
    if (
      axErr.code === 'ERR_CANCELED' ||
      axErr.name === 'CanceledError'
    ) {
      return Promise.reject(axErr)
    }
    // NexusForge：从后端错误信封提取 message，覆盖 axios 默认的 "Request failed with status code N"
    const resp = axErr.response
    if (resp && resp.data && typeof resp.data === 'object' && 'message' in resp.data) {
      const serverMsg = (resp.data as { message?: unknown }).message
      if (typeof serverMsg === 'string' && serverMsg.length > 0) {
        axErr.message = serverMsg
      }
    }
    if (cfg?.silentGlobalFeedback === true) {
      return Promise.reject(axErr)
    }
    emitAxiosFeedbackIncident(formatAxiosUserSummary(axErr), axErr)
    return Promise.reject(axErr)
  },
)

export interface ApiClient {
  get<T>(url: string, config?: AxiosRequestConfig): Promise<T>
  post<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T>
  put<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T>
  patch<T>(url: string, data?: unknown, config?: AxiosRequestConfig): Promise<T>
  delete<T>(url: string, config?: AxiosRequestConfig): Promise<T>
}

export const apiClient: ApiClient = axiosInstance as unknown as ApiClient

export interface ChapterStreamEvent {
  type:
    | 'connected'
    | 'outline_planning'
    | 'beats_planned'
    | 'chapter_start'
    | 'chapter_chunk'
    | 'chapter_content'
    | 'autopilot_stopped'
    | 'paused_for_review'
    | 'heartbeat'
  message: string
  timestamp: string
  metadata?: {
    chapter_number?: number
    chunk?: string
    beat_index?: number
    content?: string
    word_count?: number
    beats?: Array<Record<string, unknown>>
    outline_plan_mode?: string
    total_beats?: number
  }
}

export function subscribeChapterStream(
  novelId: string,
  handlers: {
    onOutlinePlanning?: (chapterNumber: number, message: string) => void
    onBeatsPlanned?: (
      chapterNumber: number,
      beats: Array<Record<string, unknown>>,
      outlinePlanMode: string,
    ) => void
    onChapterStart?: (chapterNumber: number) => void
    onChapterChunk?: (data: {
      chunk?: string
      content?: string
      beatIndex: number
      isSnapshot: boolean
    }) => void
    onChapterContent?: (data: { chapterNumber: number; content: string; wordCount: number; beatIndex: number }) => void
    onAutopilotStopped?: (status: string) => void
    /** 服务端因待审阅关闭章节流时触发，应尽快拉取 /status 同步 needs_review，避免误判断线重连 */
    onPausedForReview?: () => void
    onError?: (error: Error) => void
    onConnected?: () => void
    /** 流异常结束，可重连 */
    onDisconnected?: () => void
    /** 服务端主动结束（停止/审阅/非写作阶段关流），不应重连 */
    onStreamEnd?: (reason: 'stopped' | 'review' | 'idle') => void
  }
): AbortController {
  const ctrl = new AbortController()

  void (async () => {
    let streamTerminal: 'stopped' | 'review' | 'idle' | null = null
    try {
      const streamUrl = resolveHttpUrl(apiRoutes.novels.chapterStream(novelId))
      const streamHeaders: Record<string, string> = {
        'Accept': 'text/event-stream',
        'Cache-Control': 'no-cache',
      }
      // NexusForge：SSE 流同样需要 X-API-Key 鉴权（fetch 支持自定义头）
      const apiKey = getApiKey()
      if (apiKey) {
        streamHeaders['X-API-Key'] = apiKey
      }
      const res = await fetch(streamUrl, {
        signal: ctrl.signal,
        headers: streamHeaders,
      })

      if (!res.ok || !res.body) {
        handlers.onError?.(new Error(`HTTP ${res.status}`))
        handlers.onDisconnected?.()
        return
      }

      handlers.onConnected?.()

      const reader = res.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''

      const dispatchSseEvent = (event: ChapterStreamEvent) => {
        if (event.type === 'outline_planning' && event.metadata?.chapter_number != null) {
          handlers.onOutlinePlanning?.(event.metadata.chapter_number, event.message)
        } else if (event.type === 'beats_planned' && event.metadata?.chapter_number != null) {
          const raw = event.metadata.beats
          handlers.onBeatsPlanned?.(
            event.metadata.chapter_number,
            Array.isArray(raw) ? raw : [],
            String(event.metadata.outline_plan_mode ?? ''),
          )
        } else if (event.type === 'chapter_start' && event.metadata?.chapter_number) {
          handlers.onChapterStart?.(event.metadata.chapter_number)
        } else if (event.type === 'chapter_chunk' && event.metadata) {
          const meta = event.metadata
          if (meta.content != null && String(meta.content).length > 0) {
            handlers.onChapterChunk?.({
              content: String(meta.content),
              beatIndex: meta.beat_index || 0,
              isSnapshot: true,
            })
          } else if (meta.chunk) {
            handlers.onChapterChunk?.({
              chunk: meta.chunk,
              beatIndex: meta.beat_index || 0,
              isSnapshot: false,
            })
          }
        } else if (event.type === 'chapter_content' && event.metadata) {
          handlers.onChapterContent?.({
            chapterNumber: event.metadata.chapter_number!,
            content: event.metadata.content || '',
            wordCount: event.metadata.word_count || 0,
            beatIndex: event.metadata.beat_index || 0,
          })
        } else if (event.type === 'autopilot_stopped') {
          streamTerminal = 'stopped'
          handlers.onAutopilotStopped?.(event.message)
        } else if (event.type === 'paused_for_review') {
          streamTerminal = 'review'
          handlers.onPausedForReview?.()
        }
      }

      const flushBlocks = (buf: string): string => {
        let sepIdx: number
        let rest = buf
        while ((sepIdx = rest.indexOf('\n\n')) >= 0) {
          const block = rest.slice(0, sepIdx)
          rest = rest.slice(sepIdx + 2)
          for (const line of block.split('\n')) {
            if (!line.startsWith('data: ')) continue
            try {
              dispatchSseEvent(JSON.parse(line.slice(6)) as ChapterStreamEvent)
            } catch {
              /* 忽略残缺行 */
            }
          }
        }
        return rest
      }

      while (true) {
        const { done, value } = await reader.read()
        if (value) buffer += decoder.decode(value, { stream: true })
        buffer = flushBlocks(buffer)
        if (done) {
          buffer += decoder.decode()
          buffer = flushBlocks(buffer)
          break
        }
      }

      if (ctrl.signal.aborted) return
      if (streamTerminal) {
        handlers.onStreamEnd?.(streamTerminal)
      } else {
        // 非写作阶段等服务端关流：无 terminal 事件时也视为 idle，避免前端死循环重连
        handlers.onStreamEnd?.('idle')
      }
    } catch (e) {
      if (e instanceof Error && e.name === 'AbortError') return
      handlers.onError?.(e instanceof Error ? e : new Error('Stream error'))
      handlers.onDisconnected?.()
    }
  })()

  return ctrl
}
