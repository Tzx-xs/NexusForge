/**
 * Agent API — 对接 NexusForge 后端 /api/v1/agent/*
 *
 * 移植自 StellarScribe，适配点：
 * - 用 NexusForge 的 apiClient（axiosInstance）替换 StellarScribe 的 request
 * - SSE 流改用原生 fetch + resolveHttpUrl + getApiKey
 * - 响应信封由 axios interceptor 自动解包，业务代码直接拿 data
 */
import { apiClient } from './config'
import { resolveHttpUrl, getApiKey } from './config'

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

/** 列出会话 */
export function listConversations(novelId?: string): Promise<Conversation[]> {
  const url = novelId
    ? `/agent/conversations?novel_id=${encodeURIComponent(novelId)}`
    : '/agent/conversations'
  return apiClient.get<Conversation[]>(url) as Promise<Conversation[]>
}

/** 获取单个会话及其消息 */
export function getConversation(
  id: string
): Promise<{ conversation: Conversation; messages: Message[] }> {
  return apiClient.get<{ conversation: Conversation; messages: Message[] }>(
    `/agent/conversations/${id}`
  ) as Promise<{ conversation: Conversation; messages: Message[] }>
}

/** 删除会话 */
export function deleteConversation(id: string): Promise<{ deleted: boolean }> {
  return apiClient.delete<{ deleted: boolean }>(
    `/agent/conversations/${id}`
  ) as Promise<{ deleted: boolean }>
}

/**
 * SSE 流式 Agent 对话。
 *
 * 后端端点：POST /api/v1/agent/chat
 * 事件类型：token | tool_call | tool_result | complete | error
 *
 * 使用原生 fetch（axios 不支持 ReadableStream SSE 消费），
 * 鉴权头通过 getApiKey() 注入（与 axios interceptor 一致）。
 */
export async function* streamAgentChat(
  req: AgentChatRequest,
  signal?: AbortSignal
): AsyncGenerator<AgentEvent, void, unknown> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    'Accept': 'text/event-stream',
  }
  const apiKey = getApiKey()
  if (apiKey) {
    headers['X-API-Key'] = apiKey
  }

  const response = await fetch(resolveHttpUrl('/api/v1/agent/chat'), {
    method: 'POST',
    headers,
    body: JSON.stringify(req),
    signal,
  })

  if (!response.ok || !response.body) {
    let msg = `Agent 请求失败：HTTP ${response.status}`
    try {
      const errBody = await response.json()
      if (errBody?.message) msg = errBody.message
      else if (errBody?.detail) msg = errBody.detail
    } catch {
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

  const parseSseBlock = (block: string): { event: string; data: string } | null => {
    let event = 'message'
    let data = ''
    for (const line of block.split('\n')) {
      if (line.startsWith('event:')) {
        event = line.slice(6).trim()
      } else if (line.startsWith('data:')) {
        data += line.slice(5).trim()
      }
    }
    return data ? { event, data } : null
  }

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, '\n')
    // Phase 6 Task 6.1 修复：用 indexOf 每次只取第一个完整 SSE 块，
    // 避免 lastIndexOf 把多个事件合并成一个块导致 data 错误追加
    let sep = buffer.indexOf('\n\n')
    while (sep !== -1) {
      const ready = buffer.slice(0, sep + 2)
      buffer = buffer.slice(sep + 2)
      const parsed = parseSseBlock(ready)
      if (parsed) {
        let data: Record<string, unknown> = {}
        if (parsed.data) {
          try { data = JSON.parse(parsed.data) } catch { data = {} }
        }
        yield { type: parsed.event as AgentEventType, data }
      }
      sep = buffer.indexOf('\n\n')
    }
  }

  // 处理尾部残留
  const tail = decoder.decode()
  if (tail) buffer += tail
  if (buffer.trim()) {
    const parsed = parseSseBlock(buffer)
    if (parsed) {
      let data: Record<string, unknown> = {}
      if (parsed.data) {
        try { data = JSON.parse(parsed.data) } catch { data = {} }
      }
      yield { type: parsed.event as AgentEventType, data }
    }
  }
}
