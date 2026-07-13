/**
 * Sprint 4.4: 补全 useAiGenerate 测试。
 *
 * 为 frontend/src/composables/useAiGenerate.ts 的 SSE 解析逻辑补测试,
 * 覆盖 token 累积、isAiGenerating 切换、complete/error 终止、abort 调用。
 *
 * 策略:Mock global.fetch 与构造伪造 ReadableStream,验证 SSE 事件解析。
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

// Mock useChapterStore - 必须在 import useAiGenerate 之前
vi.mock('@/stores/chapter', () => ({
  useChapterStore: () => ({
    currentChapter: { id: 'c1' },
  }),
}))

// Mock chapters API
vi.mock('@/api/chapters', () => ({
  getGenerateContentUrl: (id: string) => `/api/v1/chapters/${id}/generate-content`,
  getAuthHeaders: () => ({}),
}))

import { useAiGenerate } from '@/composables/useAiGenerate'

// ====================================================================
// 辅助:构造伪造 SSE Response
// ====================================================================

function makeSseResponse(events: Array<{ event: string; data: any }>): Response {
  const body =
    events.map((e) => `event: ${e.event}\ndata: ${JSON.stringify(e.data)}`).join('\n\n') + '\n\n'
  const encoder = new TextEncoder()
  const stream = new ReadableStream({
    start(controller) {
      controller.enqueue(encoder.encode(body))
      controller.close()
    },
  })
  return new Response(stream, {
    status: 200,
    headers: { 'Content-Type': 'text/event-stream' },
  })
}

// ====================================================================
// Tests
// ====================================================================

describe('useAiGenerate', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.unstubAllGlobals()
  })

  it('初始状态:isAiGenerating=false、generatedContent=""、error=null、progress=0', () => {
    const editorRef = { value: null }
    const { isAiGenerating, generatedContent, error, progress } = useAiGenerate(editorRef)

    expect(isAiGenerating.value).toBe(false)
    expect(generatedContent.value).toBe('')
    expect(error.value).toBe(null)
    expect(progress.value).toBe(0)
  })

  it('token 事件累积到 generatedContent', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      makeSseResponse([
        { event: 'token', data: { delta: '你好' } },
        { event: 'token', data: { delta: '世界' } },
        { event: 'complete', data: {} },
      ])
    )
    vi.stubGlobal('fetch', fetchMock)

    const editorRef = { value: null }
    const { handleAiContinue, generatedContent } = useAiGenerate(editorRef)

    await handleAiContinue()

    expect(generatedContent.value).toBe('你好世界')
  })

  it('isAiGenerating 在流期间为 true,结束后为 false', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      makeSseResponse([
        { event: 'token', data: { delta: '测试' } },
        { event: 'complete', data: {} },
      ])
    )
    vi.stubGlobal('fetch', fetchMock)

    const editorRef = { value: null }
    const { handleAiContinue, isAiGenerating } = useAiGenerate(editorRef)

    const promise = handleAiContinue()
    // 流开始后应为 true
    expect(isAiGenerating.value).toBe(true)

    await promise
    // 流结束后应为 false
    expect(isAiGenerating.value).toBe(false)
  })

  it('complete 事件后流终止且 isAiGenerating=false', async () => {
    const fetchMock = vi.fn().mockResolvedValue(makeSseResponse([{ event: 'complete', data: {} }]))
    vi.stubGlobal('fetch', fetchMock)

    const editorRef = { value: null }
    const { handleAiContinue, isAiGenerating } = useAiGenerate(editorRef)

    await handleAiContinue()

    expect(isAiGenerating.value).toBe(false)
  })

  it('error 事件后 error 被设置且 isAiGenerating=false', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      makeSseResponse([{ event: 'error', data: { message: '生成失败' } }])
    )
    vi.stubGlobal('fetch', fetchMock)

    const editorRef = { value: null }
    const { handleAiContinue, error, isAiGenerating } = useAiGenerate(editorRef)

    await handleAiContinue()

    expect(error.value).toBe('生成失败')
    expect(isAiGenerating.value).toBe(false)
  })

  it('HTTP 错误响应(非 200)设置 error', async () => {
    const fetchMock = vi.fn().mockResolvedValue(
      new Response(null, { status: 500, statusText: 'Internal Server Error' })
    )
    vi.stubGlobal('fetch', fetchMock)

    const editorRef = { value: null }
    const { handleAiContinue, error } = useAiGenerate(editorRef)

    await handleAiContinue()

    expect(error.value).toContain('500')
  })

  it('abort 调用 AbortController.abort 使 fetch 收到 abort signal', async () => {
    const fetchMock = vi.fn().mockImplementation((_url: string, init?: RequestInit) => {
      return new Promise<Response>((_resolve, reject) => {
        // 监听 signal 的 abort 事件
        init?.signal?.addEventListener('abort', () => {
          const err = new DOMException('The user aborted a request.', 'AbortError')
          reject(err)
        })
      })
    })
    vi.stubGlobal('fetch', fetchMock)

    const editorRef = { value: null }
    const { handleAiContinue, abort, isAiGenerating } = useAiGenerate(editorRef)

    const promise = handleAiContinue()
    expect(isAiGenerating.value).toBe(true)

    abort()

    await promise

    // abort 后 isAiGenerating 应为 false(不计入 error)
    expect(isAiGenerating.value).toBe(false)
    // fetch mock 应被调用,且 init 中包含 signal
    expect(fetchMock).toHaveBeenCalled()
    const callArgs = fetchMock.mock.calls[0]
    const init = callArgs[1] as RequestInit
    expect(init.signal).toBeInstanceOf(AbortSignal)
  })
})
