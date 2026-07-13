/**
 * Sprint 5.2: AI 写作建议 SSE 流式 API。
 *
 * 调用 POST /api/v1/chapters/{chapterId}/ai-suggest,流式返回 token/complete/error 事件。
 */

import { parseSseBlocks } from '@/utils/sseParser'
import { createTimeoutSignal, combineAbortSignals } from '@/utils/abortSignalPolyfill'

export type AiSuggestEventType = 'token' | 'complete' | 'error'

export interface AiSuggestEvent {
  type: AiSuggestEventType
  data: Record<string, unknown>
}

export async function* streamAiSuggest(
  chapterId: string,
  signal?: AbortSignal
): AsyncGenerator<AiSuggestEvent, void, unknown> {
  // M-02: 统一 120 秒 SSE 超时，与调用方传入的 AbortSignal 合并
  const { signal: timeoutSignal, cleanup: timeoutCleanup } = createTimeoutSignal(120_000)
  const { signal: combinedSignal, cleanup: combineCleanup } = combineAbortSignals(
    signal ? [signal, timeoutSignal] : [timeoutSignal]
  )

  const apiKey = sessionStorage.getItem('xy-api-key')

  try {
    const response = await fetch(`/api/v1/chapters/${chapterId}/ai-suggest`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
        ...(apiKey ? { 'X-API-Key': apiKey } : {}),
      },
      signal: combinedSignal,
    })

    if (!response.ok || !response.body) {
      let msg = `AI 建议请求失败：HTTP ${response.status}`
      try {
        const errBody = await response.json()
        if (errBody?.detail) msg = errBody.detail
        else if (errBody?.message) msg = errBody.message
      } catch {
        // 忽略 JSON 解析失败
      }
      throw new Error(msg)
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, '\n')
      const lastSep = buffer.lastIndexOf('\n\n')
      if (lastSep === -1) continue
      const ready = buffer.slice(0, lastSep + 2)
      buffer = buffer.slice(lastSep + 2)
      for (const evt of parseSseBlocks(ready)) {
        let data: Record<string, unknown> = {}
        if (evt.data) {
          try { data = JSON.parse(evt.data) } catch { data = {} }
        }
        yield { type: evt.event as AiSuggestEventType, data }
      }
    }

    // 处理尾部残留
    const tail = decoder.decode()
    if (tail) buffer += tail
    if (buffer.trim()) {
      for (const evt of parseSseBlocks(buffer)) {
        let data: Record<string, unknown> = {}
        if (evt.data) {
          try { data = JSON.parse(evt.data) } catch { data = {} }
        }
        yield { type: evt.event as AiSuggestEventType, data }
      }
    }
  } finally {
    // 清理超时定时器与合并信号监听器，避免内存泄漏
    combineCleanup()
    timeoutCleanup()
  }
}
