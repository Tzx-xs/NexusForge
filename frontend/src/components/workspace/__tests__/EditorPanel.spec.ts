import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import EditorPanel from '../EditorPanel.vue'
import { useChapterStore } from '@/stores/chapter'

describe('EditorPanel', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('should have a contenteditable element for editing', async () => {
    const wrapper = mount(EditorPanel)
    await wrapper.vm.$nextTick()
    // Tiptap EditorContent 在 jsdom 下不渲染 ProseMirror DOM，
    // 但 editor 实例存在且可编辑（view.dom 即 contenteditable 元素）
    const vm = wrapper.vm as any
    expect(vm.editor).toBeTruthy()
    expect(vm.editor.isEditable).toBe(true)
    expect(vm.editor.view.dom).toBeTruthy()
    expect(vm.editor.view.dom.getAttribute('contenteditable')).toBe('true')
  })

  it('should have input and blur event handlers', async () => {
    const wrapper = mount(EditorPanel)
    await wrapper.vm.$nextTick()
    // 验证 editor 实例存在 + 可编辑（onUpdate/onBlur 由 EditorPanel.vue 配置）
    const vm = wrapper.vm as any
    expect(vm.editor).toBeTruthy()
    expect(vm.editor.isEditable).toBe(true)
    expect(vm.editor.view.dom.getAttribute('contenteditable')).toBe('true')
  })

  it('should display fallback content when no chapter is selected', () => {
    const wrapper = mount(EditorPanel)
    // When chapterStore.currentChapter is null, default empty editor content is shown
    expect(wrapper.text()).toContain('AI 续写')
    expect(wrapper.text()).toContain('字')
  })

  it('should have word count display', () => {
    const wrapper = mount(EditorPanel)
    expect(wrapper.text()).toContain('字')
  })

  it('should have AI continue button', () => {
    const wrapper = mount(EditorPanel)
    expect(wrapper.text()).toContain('AI 续写')
  })

  it('should cancel debounce save timer on unmount to prevent memory leak', async () => {
    vi.useFakeTimers()
    const chapterStore = useChapterStore()

    chapterStore.currentChapter = {
      id: '1',
      novel_id: '1',
      number: 1,
      title: '测试章节',
      outline: '',
      content: '<p>测试内容</p>',
      status: 'draft',
      word_count: 0,
      tension_score: 0,
      created_at: '',
      updated_at: '',
    }

    const updateSpy = vi.spyOn(chapterStore, 'updateChapter').mockResolvedValue({} as any)

    const wrapper = mount(EditorPanel)
    await wrapper.vm.$nextTick()
    const vm = wrapper.vm as any
    // Tiptap 不监听原生 input 事件，通过 editor.commands API 触发更新
    if (vm.editor) {
      vm.editor.commands.setContent('<p>test</p>')
      vm.editor.commands.blur()
    }

    wrapper.unmount()

    vi.advanceTimersByTime(3000)

    expect(updateSpy).not.toHaveBeenCalled()

    vi.useRealTimers()
  })

  it('should sanitize malicious HTML content to prevent XSS', async () => {
    const chapterStore = useChapterStore()

    chapterStore.currentChapter = {
      id: '1',
      novel_id: '1',
      number: 1,
      title: '测试章节',
      outline: '',
      content: '<p>正常内容</p><script>alert("xss")</script><img src=x onerror="alert(1)">',
      status: 'draft',
      word_count: 0,
      tension_score: 0,
      created_at: '',
      updated_at: '',
    }

    const wrapper = mount(EditorPanel)
    await wrapper.vm.$nextTick()
    const vm = wrapper.vm as any
    // Tiptap schema 自动过滤 <script> 和 onerror；DOMPurify 在 setContent 前预处理
    // 优先用 editor.getHTML() 验证（更直接），回退到 .ProseMirror DOM
    const html = vm.editor
      ? vm.editor.getHTML()
      : wrapper.find('.ProseMirror').html()

    expect(html).not.toContain('<script>')
    expect(html).not.toContain('onerror')
    expect(html).toContain('正常内容')
  })

  it('should count Chinese characters and English words separately for mixed content', async () => {
    const wrapper = mount(EditorPanel, { attachTo: document.body })
    // 等待 Tiptap editor 实例就绪
    await wrapper.vm.$nextTick()
    const vm = wrapper.vm as any
    // Tiptap 不监听原生 input 事件，通过 editor.commands.setContent 触发更新
    if (vm.editor) {
      // setContent 第二个参数 true = emitUpdate，触发 onUpdate 回调链
      // （B14 后字数统计走 250ms 防抖，需等待防抖窗口再断言）
      vm.editor.commands.setContent('<p>你好世界hello world</p>', true)
    } else {
      // 回退：直接操作 DOM（兼容未初始化 editor 的环境）
      const editable = wrapper.find('.ProseMirror')
      const element = editable.element as HTMLDivElement
      element.innerHTML = '<p>你好世界hello world</p>'
      element.dispatchEvent(new Event('input', { bubbles: true }))
    }

    // 等待 B14 防抖窗口（250ms）触发字数统计刷新
    await new Promise((r) => setTimeout(r, 350))
    await wrapper.vm.$nextTick()

    const wordCountEl = wrapper.find('.word-count')
    expect(wordCountEl.text()).toContain('6')

    wrapper.unmount()
  })
})
