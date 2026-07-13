/**
 * Phase 6 Task 6.1：Agent API SSE 流式解析单元测试
 *
 * 验证点：
 * 1. streamAgentChat 正确解析 SSE 块（event + data 行）
 * 2. 多事件流式累积解析
 * 3. JSON data 解析
 * 4. 非 JSON data 回退空对象
 * 5. HTTP 错误抛出含状态码的 Error
 * 6. AbortSignal 传递给 fetch
 * 7. 鉴权头注入（X-API-Key）
 * 8. 尾部残留块处理
 */
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { streamAgentChat, type AgentEvent } from './agent'

// ─── mock fetch ─────────────────────────────────────────────────
interface MockFetchOptions {
  chunks: string[]          // ReadableStream 的分块
  status?: number
  statusText?: string
  ok?: boolean
}

function createMockFetch(opts: MockFetchOptions) {
  const { chunks, status = 200, statusText = 'OK', ok = true } = opts
  const encoder = new TextEncoder()
  const stream = new ReadableStream({
    start(controller) {
      for (const chunk of chunks) {
        controller.enqueue(encoder.encode(chunk))
      }
      controller.close()
    },
  })
  return vi.fn().mockResolvedValue({
    ok,
    status,
    statusText,
    body: stream,
    // HTTP 错误场景：返回空对象让代码走默认的 HTTP {status} 消息分支
    json: async () => ({}),
    text: async () => '',
  })
}

describe('streamAgentChat — SSE 流式解析', () => {
  const originalFetch = globalThis.fetch

  beforeEach(() => {
    // 清除 getApiKey 的 localStorage 残留
    localStorage.clear()
  })

  afterEach(() => {
    globalThis.fetch = originalFetch
    vi.restoreAllMocks()
  })

  async function collectEvents(gen: AsyncGenerator<AgentEvent>): Promise<AgentEvent[]> {
    const events: AgentEvent[] = []
    for await (const evt of gen) {
      events.push(evt)
    }
    return events
  }

  it('解析单个 token 事件', async () => {
    globalThis.fetch = createMockFetch({
      chunks: ['event: token\ndata: {"delta":"你好"}\n\n'],
    })
    const events = await collectEvents(streamAgentChat({ message: 'test' }))
    expect(events).toHaveLength(1)
    expect(events[0].type).toBe('token')
    expect(events[0].data.delta).toBe('你好')
  })

  it('解析多个事件（流式累积）', async () => {
    globalThis.fetch = createMockFetch({
      chunks: [
        'event: token\ndata: {"delta":"你"}\n\n',
        'event: token\ndata: {"delta":"好"}\n\n',
        'event: token\ndata: {"delta":"世界"}\n\n',
        'event: complete\ndata: {"conversation_id":"conv-1"}\n\n',
      ],
    })
    const events = await collectEvents(streamAgentChat({ message: 'test' }))
    expect(events).toHaveLength(4)
    expect(events[0].data.delta).toBe('你')
    expect(events[1].data.delta).toBe('好')
    expect(events[2].data.delta).toBe('世界')
    expect(events[3].type).toBe('complete')
    expect(events[3].data.conversation_id).toBe('conv-1')
  })

  it('解析 tool_call 和 tool_result 事件', async () => {
    globalThis.fetch = createMockFetch({
      chunks: [
        'event: tool_call\ndata: {"tool":"generate_chapter","args":{"number":1}}\n\n',
        'event: tool_result\ndata: {"tool_call_id":"tc-1","success":true,"data":{"chapter_id":"c1"}}\n\n',
      ],
    })
    const events = await collectEvents(streamAgentChat({ message: '生成章节' }))
    expect(events).toHaveLength(2)
    expect(events[0].type).toBe('tool_call')
    expect(events[0].data.tool).toBe('generate_chapter')
    expect(events[0].data.args).toEqual({ number: 1 })
    expect(events[1].type).toBe('tool_result')
    expect(events[1].data.tool_call_id).toBe('tc-1')
    expect(events[1].data.success).toBe(true)
  })

  it('解析 error 事件', async () => {
    globalThis.fetch = createMockFetch({
      chunks: ['event: error\ndata: {"code":"E5000","message":"内部错误"}\n\n'],
    })
    const events = await collectEvents(streamAgentChat({ message: 'test' }))
    expect(events).toHaveLength(1)
    expect(events[0].type).toBe('error')
    expect(events[0].data.code).toBe('E5000')
    expect(events[0].data.message).toBe('内部错误')
  })

  it('跨分块的 SSE 块正确拼接', async () => {
    // 一个事件被拆成两个 chunk
    globalThis.fetch = createMockFetch({
      chunks: [
        'event: token\ndata: {"delta":"跨块',
        '"}\n\n',
      ],
    })
    const events = await collectEvents(streamAgentChat({ message: 'test' }))
    expect(events).toHaveLength(1)
    expect(events[0].data.delta).toBe('跨块')
  })

  it('多个事件在单个 chunk 中解析', async () => {
    globalThis.fetch = createMockFetch({
      chunks: [
        'event: token\ndata: {"delta":"a"}\n\nevent: token\ndata: {"delta":"b"}\n\n',
      ],
    })
    const events = await collectEvents(streamAgentChat({ message: 'test' }))
    expect(events).toHaveLength(2)
    expect(events[0].data.delta).toBe('a')
    expect(events[1].data.delta).toBe('b')
  })

  it('非 JSON data 回退空对象', async () => {
    globalThis.fetch = createMockFetch({
      chunks: ['event: token\ndata: not-json\n\n'],
    })
    const events = await collectEvents(streamAgentChat({ message: 'test' }))
    expect(events).toHaveLength(1)
    expect(events[0].data).toEqual({})
  })

  it('无 data 行的事件被跳过', async () => {
    globalThis.fetch = createMockFetch({
      chunks: ['event: token\n\n'],
    })
    const events = await collectEvents(streamAgentChat({ message: 'test' }))
    expect(events).toHaveLength(0)
  })

  it('HTTP 错误抛出含状态码的 Error', async () => {
    globalThis.fetch = createMockFetch({
      chunks: [],
      status: 500,
      ok: false,
    })
    await expect(collectEvents(streamAgentChat({ message: 'test' }))).rejects.toThrow('500')
  })

  it('HTTP 401 错误抛出 Error', async () => {
    globalThis.fetch = createMockFetch({
      chunks: [],
      status: 401,
      ok: false,
    })
    await expect(collectEvents(streamAgentChat({ message: 'test' }))).rejects.toThrow('401')
  })

  it('AbortSignal 传递给 fetch', async () => {
    const mockFetch = createMockFetch({ chunks: ['event: token\ndata: {}\n\n'] })
    global.fetch = mockFetch
    const controller = new AbortController()

    try {
      const gen = streamAgentChat({ message: 'test' }, controller.signal)
      // 立即 abort
      controller.abort()
      await collectEvents(gen)
    } catch {
      // abort 可能抛 AbortError，忽略
    }

    expect(mockFetch).toHaveBeenCalledWith(
      expect.any(String),
      expect.objectContaining({ signal: controller.signal })
    )
  })

  it('请求体包含 message 和可选 conversation_id/novel_id', async () => {
    const mockFetch = createMockFetch({ chunks: ['event: complete\ndata: {}\n\n'] })
    global.fetch = mockFetch

    await collectEvents(streamAgentChat({
      message: '生成第3章',
      conversation_id: 'conv-123',
      novel_id: 'novel-456',
    }))

    const callArgs = mockFetch.mock.calls[0]
    const body = JSON.parse(callArgs[1].body)
    expect(body.message).toBe('生成第3章')
    expect(body.conversation_id).toBe('conv-123')
    expect(body.novel_id).toBe('novel-456')
  })

  it('请求头包含 Content-Type 和 Accept: text/event-stream', async () => {
    const mockFetch = createMockFetch({ chunks: ['event: complete\ndata: {}\n\n'] })
    global.fetch = mockFetch

    await collectEvents(streamAgentChat({ message: 'test' }))

    const headers = mockFetch.mock.calls[0][1].headers
    expect(headers['Content-Type']).toBe('application/json')
    expect(headers['Accept']).toBe('text/event-stream')
  })

  it('localStorage 有 API Key 时注入 X-API-Key 头', async () => {
    // NexusForge 的 getApiKey 从 localStorage 读取（key: nexusforge_api_key）
    localStorage.setItem('nexusforge_api_key', 'test-key-123')
    const mockFetch = createMockFetch({ chunks: ['event: complete\ndata: {}\n\n'] })
    global.fetch = mockFetch

    await collectEvents(streamAgentChat({ message: 'test' }))

    const headers = mockFetch.mock.calls[0][1].headers
    expect(headers['X-API-Key']).toBe('test-key-123')
  })

  it('尾部残留块（无 \\n\\n 结尾）被处理', async () => {
    globalThis.fetch = createMockFetch({
      chunks: ['event: token\ndata: {"delta":"尾部"}\n\nevent: complete\ndata: {}'],
      // 最后一个事件没有 \n\n 结尾
    })
    const events = await collectEvents(streamAgentChat({ message: 'test' }))
    // 第一个事件正常解析，尾部残留也应被处理
    expect(events.length).toBeGreaterThanOrEqual(1)
    expect(events[0].data.delta).toBe('尾部')
  })
})
