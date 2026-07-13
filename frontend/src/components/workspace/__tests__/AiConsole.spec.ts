import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia, type Pinia } from 'pinia'

// =========================================================================
// Mock 模块（必须在顶层 — vi.mock 会被提升到文件顶部）
// =========================================================================

// Mock vue-router：提供 route params（novelId, chapterId）
vi.mock('vue-router', () => ({
  useRoute: () => ({
    params: { novelId: 'n1', chapterId: 'c1' },
  }),
}))

// Mock naive-ui 图标组件
vi.mock('@vicons/tabler', () => ({
  PlayerPlay: { name: 'PlayerPlay', template: '<span>▶</span>' },
  Robot: { name: 'Robot', template: '<span>🤖</span>' },
  Shield: { name: 'Shield', template: '<span>🛡</span>' },
  Ban: { name: 'Ban', template: '<span>🚫</span>' },
  Star: { name: 'Star', template: '<span>⭐</span>' },
  MessageCircle: { name: 'MessageCircle', template: '<span>💬</span>' },
}))

// Mock naive-ui 离散组件 (NSelect, NSwitch, NSlider)
vi.mock('naive-ui', () => ({
  NSelect: {
    name: 'NSelect',
    template: '<select><slot /></select>',
    props: ['value', 'options', 'size'],
  },
  NSwitch: {
    name: 'NSwitch',
    template: '<input type="checkbox" />',
    props: ['value', 'size'],
  },
  NSlider: {
    name: 'NSlider',
    template: '<input type="range" />',
    props: ['value', 'min', 'max'],
  },
}))

// Mock 子面板组件（AiConsole 内引用的 tab 内容组件）
vi.mock('@/components/quality/QualityPanel.vue', () => ({
  default: { name: 'QualityPanel', template: '<div class="quality-panel" />' },
}))
vi.mock('@/components/voice/VoicePanel.vue', () => ({
  default: { name: 'VoicePanel', template: '<div class="voice-panel" />' },
}))
vi.mock('@/components/workspace/IronLockPanel.vue', () => ({
  default: { name: 'IronLockPanel', template: '<div class="ironlock-panel" />' },
}))
vi.mock('@/components/workspace/ForeshadowPanel.vue', () => ({
  default: { name: 'ForeshadowPanel', template: '<div class="foreshadow-panel" />' },
}))

// Mock chapters API
vi.mock('@/api/chapters', () => ({
  getGenerateContentUrl: (id: string) => `/api/v1/chapters/${id}/generate-content`,
  getAuthHeaders: () => ({}),
}))

// Mock autonomous API
vi.mock('@/api/autonomous', () => ({
  createSession: vi.fn(),
  startSession: vi.fn(),
  getSession: vi.fn(),
  cancelSession: vi.fn(),
}))

// Mock toast — 使用 vi.hoisted 避免 TDZ 错误：vi.mock 被提升到文件顶部，需同步初始化
const mockToast = vi.hoisted(() => ({
  success: vi.fn(),
  error: vi.fn(),
  warning: vi.fn(),
  info: vi.fn(),
}))
vi.mock('@/utils/toast', () => ({
  toast: mockToast,
}))

// =========================================================================
// 受测组件
// =========================================================================
import AiConsole from '../AiConsole.vue'

describe('AiConsole', () => {
  let pinia: Pinia

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vi.clearAllMocks()
  })

  function mountConsole(props: Record<string, unknown> = {}) {
    return mount(AiConsole, {
      props: {
        content: '',
        chapterId: 'c1',
        characterNames: ['张三', '李四'],
        locationNames: ['长安', '洛阳'],
        baselineFpId: 'fp-001',
        ...props,
      },
      global: { plugins: [pinia] },
    })
  }

  // -----------------------------------------------------------------------
  // Test 1: 组件渲染 — tabs 和模式选择器正确渲染
  // -----------------------------------------------------------------------
  it('1. 组件渲染：标签页和生成模式选择器正确渲染', () => {
    const wrapper = mountConsole()

    // 六个标签页
    const tabLabels = ['生成', '质检', '文风', '铁锁', '伏笔', '历史']
    for (const label of tabLabels) {
      expect(wrapper.text()).toContain(label)
    }

    // 四个生成模式
    const modeLabels = ['续写', '改写', '扩写', '守护']
    for (const label of modeLabels) {
      expect(wrapper.text()).toContain(label)
    }

    // 生成按钮和自动驾驶按钮
    expect(wrapper.find('.generate-btn').exists()).toBe(true)
    expect(wrapper.find('.auto-btn').exists()).toBe(true)
  })

  // -----------------------------------------------------------------------
  // Test 2: 标签页切换
  // -----------------------------------------------------------------------
  it('2. 标签页切换：点击标签页切换显示对应内容', async () => {
    const wrapper = mountConsole()

    // 初始在"生成" tab
    expect(wrapper.find('.generate-section').exists()).toBe(true)

    // 切换到"质检"
    const qualityTab = wrapper.findAll('.tab-btn').find((b) => b.text() === '质检')
    expect(qualityTab).toBeTruthy()
    await qualityTab!.trigger('click')
    await flushPromises()

    // 质检面板应显示
    expect(wrapper.find('.quality-panel').exists()).toBe(true)
  })

  // -----------------------------------------------------------------------
  // Test 3: 参数绑定 — targetLength / styleStrength / creativity
  // -----------------------------------------------------------------------
  it('3. 参数绑定：targetLength、styleStrength、creativity 值正确绑定', () => {
    const wrapper = mountConsole()

    // 获取组件实例中暴露的内部状态
    const vm = wrapper.vm as unknown as {
      targetLength: string
      styleStrength: number
      creativity: number
    }

    expect(vm.targetLength).toBe('medium')
    expect(vm.styleStrength).toBe(70)
    expect(vm.creativity).toBe(50)
  })

  // -----------------------------------------------------------------------
  // Test 4: 生成按钮触发 — loading 状态正确切换
  // -----------------------------------------------------------------------
  it('4. 生成按钮触发 — 开始生成后进入 loading 状态', async () => {
    // Mock fetch 永远不 resolve（模拟生成中）
    const mockFetch = vi.fn().mockImplementation(
      () =>
        new Promise<Response>(() => {
          /* 永不 resolve — 模拟进行中的 SSE */
        })
    )
    globalThis.fetch = mockFetch

    const wrapper = mountConsole()
    const generateBtn = wrapper.find('.generate-btn')

    expect(generateBtn.attributes('disabled')).toBeUndefined()

    // 点击生成
    await generateBtn.trigger('click')
    await flushPromises()

    // fetch 应该被调用
    expect(mockFetch).toHaveBeenCalled()

    // 由于 mock fetch 永不 resolve，组件应仍处于 generating 状态
    // generateBtn 应变为 disabled
    expect(generateBtn.attributes('disabled')).toBeDefined()
  })

  // -----------------------------------------------------------------------
  // Test 5: SSE 错误事件 → toast.error 被调用
  // -----------------------------------------------------------------------
  it('5. SSE error 事件：error 事件触发后调用 toast.error', async () => {
    // 构造一个返回 SSE error 事件的 ReadableStream
    const encoder = new TextEncoder()
    const errorStream = new ReadableStream({
      start(controller) {
        const eventBlock = 'event: error\ndata: {"message":"生成内容违规"}\n\n'
        controller.enqueue(encoder.encode(eventBlock))
        controller.close()
      },
    })

    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      body: errorStream,
      json: vi.fn(),
      text: vi.fn(),
    } as unknown as Response)
    globalThis.fetch = mockFetch

    const wrapper = mountConsole()
    await wrapper.find('.generate-btn').trigger('click')
    await flushPromises()
    // 等待 SSE 流消费
    await new Promise((resolve) => setTimeout(resolve, 50))
    await flushPromises()

    expect(mockToast.error).toHaveBeenCalledWith('生成内容违规')
  })

  // -----------------------------------------------------------------------
  // Test 6: SSE token 事件 → content 流式更新
  // -----------------------------------------------------------------------
  it('6. SSE token 事件：token 事件触发 content 流式更新', async () => {
    const encoder = new TextEncoder()
    const tokenStream = new ReadableStream({
      start(controller) {
        const eventBlock =
          'event: token\ndata: {"delta":"天空一片蔚蓝"}\n\nevent: token\ndata: {"delta":"，万里无云"}\n\nevent: complete\ndata: {"chapter_id":"c1"}\n\n'
        controller.enqueue(encoder.encode(eventBlock))
        controller.close()
      },
    })

    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      body: tokenStream,
      json: vi.fn(),
      text: vi.fn(),
    } as unknown as Response)
    globalThis.fetch = mockFetch

    const wrapper = mountConsole()
    await wrapper.find('.generate-btn').trigger('click')
    await flushPromises()
    await new Promise((resolve) => setTimeout(resolve, 50))
    await flushPromises()

    // 验证 toast.success 被调用（complete 事件）
    expect(mockToast.success).toHaveBeenCalledWith('生成完成')
  })

  // -----------------------------------------------------------------------
  // Test 7: Abort 中断 — 用户点击取消
  // -----------------------------------------------------------------------
  it('7. Abort 中断：快速点击生成后立即中止，AbortSignal 被触发', async () => {
    // 使用 AbortError 模拟 fetch 被中止
    const mockFetch = vi.fn().mockRejectedValue(
      Object.assign(new Error('The user aborted a request'), { name: 'AbortError' })
    )
    globalThis.fetch = mockFetch

    const wrapper = mountConsole()
    await wrapper.find('.generate-btn').trigger('click')
    await flushPromises()

    // AbortError 被静默处理，toast.info 提示取消
    expect(mockToast.info).toHaveBeenCalledWith('已取消生成')
  })

  // -----------------------------------------------------------------------
  // Test 8: 自动驾驶按钮交互
  // -----------------------------------------------------------------------
  it('8. 自动驾驶按钮：点击触发 toggleAutopilot 流程', async () => {
    const { createSession, startSession } = await import('@/api/autonomous')

    ;(createSession as ReturnType<typeof vi.fn>).mockResolvedValue({
      session_id: 'sess-001',
      current_chapter_index: 0,
      target_chapters: 10,
      total_words_generated: 0,
    })
    ;(startSession as ReturnType<typeof vi.fn>).mockResolvedValue({ ok: true })

    const wrapper = mountConsole()
    const autoBtn = wrapper.find('.auto-btn')

    await autoBtn.trigger('click')
    await flushPromises()

    // createSession 和 startSession 应被调用
    expect(createSession).toHaveBeenCalledWith({ novel_id: 'n1' })
    expect(startSession).toHaveBeenCalledWith('sess-001')

    // toast 提示启动成功
    expect(mockToast.success).toHaveBeenCalledWith('自动驾驶已启动')
  })
})
