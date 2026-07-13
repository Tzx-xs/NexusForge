import request from './http'
import { parseSseBlocks } from '@/utils/sseParser'
import { createTimeoutSignal, combineAbortSignals } from '@/utils/abortSignalPolyfill'

export interface Conversation {
  id: string
  novel_id: string | null
  title: string | null
  created_at: string
  updated_at: string
}

export interface Message {
  id: string
  conversation_id: string
  role: 'user' | 'assistant'
  content: string
  tool_calls: string | null
  created_at: string
}

export interface AgentChatRequest {
  conversation_id?: string | null
  message: string
  novel_id?: string | null
}

export type AgentEventType = 'token' | 'tool_call' | 'tool_result' | 'complete' | 'error'

export interface AgentEvent {
  type: AgentEventType
  data: Record<string, unknown>
}

export function listConversations(novelId?: string): Promise<Conversation[]> {
  const url = novelId ? `/agent/conversations?novel_id=${novelId}` : '/agent/conversations'
  return request.get<Conversation[]>(url)
}

export function getConversation(
  id: string
): Promise<{ conversation: Conversation; messages: Message[] }> {
  return request.get<{ conversation: Conversation; messages: Message[] }>(
    `/agent/conversations/${id}`
  )
}

export function deleteConversation(id: string): Promise<{ deleted: boolean }> {
  return request.delete<{ deleted: boolean }>(`/agent/conversations/${id}`)
}

export async function* streamAgentChat(
  req: AgentChatRequest,
  signal?: AbortSignal
): AsyncGenerator<AgentEvent, void, unknown> {
  // M-02: 统一 120 秒 SSE 超时，与调用方传入的 AbortSignal 合并
  const { signal: timeoutSignal, cleanup: timeoutCleanup } = createTimeoutSignal(120_000)
  const { signal: combinedSignal, cleanup: combineCleanup } = combineAbortSignals(
    signal ? [signal, timeoutSignal] : [timeoutSignal]
  )

  // 使用原生 fetch 而非 axios.request：axios 不支持 ReadableStream SSE 消费
  // SSE 请求同样需要认证头，直接从 sessionStorage 读取
  const apiKey = sessionStorage.getItem('xy-api-key')

  try {
    const response = await fetch('/api/v1/agent/chat', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
        ...(apiKey ? { 'X-API-Key': apiKey } : {}),
      },
      body: JSON.stringify(req),
      signal: combinedSignal,
    })

    if (!response.ok || !response.body) {
      let msg = `Agent 请求失败：HTTP ${response.status}`
      try {
        const errBody = await response.json()
        if (errBody?.detail) msg = errBody.detail
        else if (errBody?.message) msg = errBody.message
      } catch {
        // JSON 解析失败，尝试读取纯文本 body
        try {
          const textBody = await response.text()
          if (textBody) msg += `：${textBody.slice(0, 200)}`
        } catch {
          // 忽略
        }
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
        yield { type: evt.event as AgentEventType, data }
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
        yield { type: evt.event as AgentEventType, data }
      }
    }
  } finally {
    // 清理超时定时器与合并信号监听器，避免内存泄漏
    combineCleanup()
    timeoutCleanup()
  }
}
