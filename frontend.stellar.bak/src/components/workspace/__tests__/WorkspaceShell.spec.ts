import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia, type Pinia } from 'pinia'
import { ref } from 'vue'

// Mock vue-router（避免真实路由依赖）
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
  useRoute: () => ({ params: { chapterId: 'c1' }, query: {} }),
}))

// Mock useCurrentNovelId（避免依赖 router/store 链）
vi.mock('@/composables/useCurrentNovelId', () => ({
  useCurrentNovelId: () => ({ novelId: ref('n1') }),
}))

// Mock toast
vi.mock('@/utils/toast', () => ({
  toast: {
    info: vi.fn(),
    success: vi.fn(),
    error: vi.fn(),
    warning: vi.fn(),
  },
}))

// Mock snapshots API 避免 historyStore.open 触发真实 axios 请求
vi.mock('@/api/snapshots', () => ({
  listSnapshots: vi.fn().mockResolvedValue([]),
  listChapterSnapshots: vi.fn().mockResolvedValue([]),
  createSnapshot: vi.fn(),
  getSnapshot: vi.fn(),
  deleteSnapshot: vi.fn(),
}))

// Mock XyDrawer 与 AgentChatPanel 避免深渲染
vi.mock('@/components/common', () => ({
  XyDrawer: {
    name: 'XyDrawer',
    template: '<div><slot /></div>',
  },
  XyDialog: {
    name: 'XyDialog',
    template: '<div><slot /></div>',
  },
}))

vi.mock('../AgentChatPanel.vue', () => ({
  default: { name: 'AgentChatPanel', template: '<div class="agent-stub" />' },
}))

// Mock 即将创建的弹窗组件（GREEN 阶段会实现真实组件）
vi.mock('../GlobalSearchModal.vue', () => ({
  default: { name: 'GlobalSearchModal', template: '<div class="search-modal-stub" />' },
}))

vi.mock('../HistoryModal.vue', () => ({
  default: { name: 'HistoryModal', template: '<div class="history-modal-stub" />' },
}))

// Sprint 5.2: Mock AiSuggestPopover,接收 visible prop 以便验证 Bulb 按钮接入
vi.mock('../AiSuggestPopover.vue', () => ({
  default: {
    name: 'AiSuggestPopover',
    template: '<div class="ai-suggest-stub" />',
    props: ['visible'],
  },
}))

import WorkspaceShell from '../WorkspaceShell.vue'
import { useSearchStore } from '@/stores/search'
import { useHistoryStore } from '@/stores/history'

describe('WorkspaceShell', () => {
  let pinia: Pinia

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vi.clearAllMocks()
  })

  function mountShell() {
    return mount(WorkspaceShell, {
      global: {
        plugins: [pinia],
        stubs: {
          XyDrawer: true,
          AgentChatPanel: true,
          GlobalSearchModal: true,
          HistoryModal: true,
        },
      },
    })
  }

  it('Search 按钮无 disabled 属性（已接入功能）', () => {
    const wrapper = mountShell()
    const searchBtn = wrapper.find('.search-btn')
    expect(searchBtn.exists()).toBe(true)
    expect(searchBtn.attributes('disabled')).toBeUndefined()
  })

  it('点击 Search 按钮 → searchStore.visible 为 true', async () => {
    const wrapper = mountShell()
    const searchStore = useSearchStore()
    expect(searchStore.visible).toBe(false)

    await wrapper.find('.search-btn').trigger('click')
    expect(searchStore.visible).toBe(true)
  })

  it('Bulb 按钮无 disabled 属性（已接入功能）', () => {
    const wrapper = mountShell()
    const bulbBtn = wrapper.find('button[aria-label="AI 建议"]')
    expect(bulbBtn.exists()).toBe(true)
    expect(bulbBtn.attributes('disabled')).toBeUndefined()
  })

  it('点击 Bulb 按钮 → AiSuggestPopover visible 变为 true', async () => {
    const wrapper = mountShell()
    const popover = wrapper.findComponent({ name: 'AiSuggestPopover' })
    expect(popover.exists()).toBe(true)
    // 初始 visible 为 false
    expect(popover.props('visible')).toBe(false)

    await wrapper.find('button[aria-label="AI 建议"]').trigger('click')
    // 点击后 visible 变为 true
    expect(popover.props('visible')).toBe(true)
  })

  it('Clock 按钮无 disabled 属性（已接入功能）', () => {
    const wrapper = mountShell()
    const clockBtn = wrapper.find('button[aria-label="历史记录"]')
    expect(clockBtn.exists()).toBe(true)
    expect(clockBtn.attributes('disabled')).toBeUndefined()
  })

  it('点击 Clock 按钮 → historyStore.visible 为 true', async () => {
    const wrapper = mountShell()
    const historyStore = useHistoryStore()
    expect(historyStore.visible).toBe(false)

    await wrapper.find('button[aria-label="历史记录"]').trigger('click')
    expect(historyStore.visible).toBe(true)
  })

  it('More 按钮无 disabled 属性（已接入功能）', () => {
    const wrapper = mountShell()
    const moreBtn = wrapper.find('button[aria-label="更多"]')
    expect(moreBtn.exists()).toBe(true)
    expect(moreBtn.attributes('disabled')).toBeUndefined()
  })

  it('点击 More 按钮 → 下拉菜单出现（moreMenuVisible 切换）', async () => {
    const wrapper = mountShell()

    // 初始无下拉菜单
    expect(wrapper.find('.more-menu').exists()).toBe(false)

    await wrapper.find('button[aria-label="更多"]').trigger('click')
    expect(wrapper.find('.more-menu').exists()).toBe(true)
  })

  it('渲染时 GlobalSearchModal 与 HistoryModal 组件挂载', () => {
    const wrapper = mountShell()
    expect(wrapper.findComponent({ name: 'GlobalSearchModal' }).exists()).toBe(true)
    expect(wrapper.findComponent({ name: 'HistoryModal' }).exists()).toBe(true)
  })
})
