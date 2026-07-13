import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia, type Pinia } from 'pinia'
import { ref } from 'vue'

// Mock vue-router
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

// Mock useCurrentNovelId
vi.mock('@/composables/useCurrentNovelId', () => ({
  useCurrentNovelId: () => ({ novelId: ref('n1') }),
}))

// Mock toast
vi.mock('@/utils/toast', () => ({
  toast: { info: vi.fn(), success: vi.fn(), error: vi.fn(), warning: vi.fn() },
}))

// Mock naive-ui 组件为简单 slot 容器
vi.mock('naive-ui', () => ({
  NButton: { template: '<button><slot /></button>' },
  NModal: {
    props: ['show', 'title'],
    template: '<div v-if="show" class="n-modal-stub"><slot /></div>',
  },
  NForm: { template: '<div><slot /></div>' },
  NFormItem: { props: ['label'], template: '<div><slot /></div>' },
  NInput: { props: ['value'], template: '<input />' },
  NSelect: { props: ['value', 'options'], template: '<select />' },
}))

// Mock bibleStore:提供带 chapterAppearances/relations 的 character
vi.mock('@/stores/bible', () => ({
  useBibleStore: () => ({
    characters: [
      {
        id: 'c1',
        novel_id: 'n1',
        name: '唐凌轩',
        role: '主角',
        description: '测试描述',
        personality: '冷静,坚毅',
        background: '出身不凡',
        appearance: '',
        created_at: '',
        updated_at: '',
        // Sprint 6.2: 扩展字段
        chapterAppearances: [{ title: '第1章' }, { title: '第3章' }],
        relations: [{ name: '韩铮' }, { name: '李振' }],
      },
    ],
    loading: false,
    error: null,
    fetchCharacters: vi.fn().mockResolvedValue(undefined),
  }),
}))

// Mock novelStore
vi.mock('@/stores/novel', () => ({
  useNovelStore: () => ({
    novels: [{ id: 'n1', title: '测试小说' }],
    fetchNovels: vi.fn().mockResolvedValue(undefined),
  }),
}))

import CharactersPage from '@/views/CharactersPage.vue'

describe('CharactersPage Sprint 6.2: 占位符修复', () => {
  let pinia: Pinia

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
    vi.clearAllMocks()
  })

  function mountPage() {
    return mount(CharactersPage, {
      global: { plugins: [pinia] },
    })
  }

  async function openFirstCharacter() {
    const wrapper = mountPage()
    await flushPromises()
    // 点击第一个 character 卡片打开 detail drawer
    const card = wrapper.find('.character-card')
    if (card.exists()) {
      await card.trigger('click')
      await flushPromises()
    }
    return wrapper
  }

  it('人物有出场章节时显示章节标题列表(非 "—")', async () => {
    const wrapper = await openFirstCharacter()
    // detail drawer 应存在
    expect(wrapper.find('.detail-drawer').exists()).toBe(true)
    // 出场章节 info-item 应包含"第1章",而非 "—"
    const chapterItem = wrapper.findAll('.info-item')[0]
    expect(chapterItem.exists()).toBe(true)
    const chapterValue = chapterItem.find('.info-value')
    expect(chapterValue.text()).toContain('第1章')
    expect(chapterValue.text()).not.toBe('—')
  })

  it('人物有关联人物时显示关联名字列表(非 "—")', async () => {
    const wrapper = await openFirstCharacter()
    const relationItem = wrapper.findAll('.info-item')[1]
    expect(relationItem.exists()).toBe(true)
    const relationValue = relationItem.find('.info-value')
    expect(relationValue.text()).toContain('韩铮')
    expect(relationValue.text()).not.toBe('—')
  })
})
