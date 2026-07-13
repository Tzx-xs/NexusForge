import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia, type Pinia } from 'pinia'

// 使用 vi.hoisted 确保 mock 函数在 vi.mock 工厂执行前已初始化
const { mockStreamAiSuggest } = vi.hoisted(() => ({
  mockStreamAiSuggest: vi.fn(),
}))

// Mock chapterStore(提供 chapterId)
vi.mock('@/stores/chapter', () => ({
  useChapterStore: () => ({
    currentChapter: { id: 'c1' },
  }),
}))

// Mock toast(组件可能调用)
vi.mock('@/utils/toast', () => ({
  toast: { info: vi.fn(), success: vi.fn(), error: vi.fn(), warning: vi.fn() },
}))

// Mock aiSuggest API
vi.mock('@/api/aiSuggest', () => ({
  streamAiSuggest: mockStreamAiSuggest,
}))

import AiSuggestPopover from '../AiSuggestPopover.vue'

describe('AiSuggestPopover', () => {
  let pinia: Pinia

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vi.clearAllMocks()

    // 默认 mock 返回正常流(token + complete)
    mockStreamAiSuggest.mockImplementation(() => {
      return (async function* () {
        yield { type: 'token', data: { delta: '建议1' } }
        yield { type: 'token', data: { delta: '建议2' } }
        yield { type: 'complete', data: { chapter_id: 'c1' } }
      })()
    })
  })

  function mountPopover(visible = true) {
    return mount(AiSuggestPopover, {
      props: { visible },
      global: { plugins: [pinia] },
    })
  }

  async function flushAll() {
    // 多次 flush 确保 async generator 完全消费
    await flushPromises()
    await new Promise((resolve) => setTimeout(resolve, 10))
    await flushPromises()
  }

  it('1. visible=false 时不渲染浮层内容', () => {
    const wrapper = mountPopover(false)
    expect(wrapper.find('.ai-suggest-content').exists()).toBe(false)
  })

  it('2. visible=true 时显示浮层内容', async () => {
    const wrapper = mountPopover(true)
    await flushAll()
    expect(wrapper.find('.ai-suggest-content').exists()).toBe(true)
  })

  it('3. 打开浮层触发 streamAiSuggest 调用', async () => {
    mountPopover(true)
    await flushAll()
    expect(mockStreamAiSuggest).toHaveBeenCalledWith('c1', expect.anything())
  })

  it('4. token 事件累加到建议文本', async () => {
    const wrapper = mountPopover(true)
    await flushAll()
    expect(wrapper.find('.suggest-text').text()).toContain('建议1建议2')
  })

  it('5. complete 事件关闭 loading 状态', async () => {
    const wrapper = mountPopover(true)
    await flushAll()
    // complete 后 loading 应消失
    expect(wrapper.find('.loading-indicator').exists()).toBe(false)
  })
})
