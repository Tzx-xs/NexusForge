/**
 * 写作功能专项测试项目（Writing Feature Test Suite）
 * --------------------------------------------------
 * 目标：系统性验证星渊笔「写作功能」的核心链路是否工作正常：
 *   A. 字数统计（纯函数 + 立即更新 + 防抖更新 B14）
 *   B. EditorPanel 集成（章节加载即时字数、打字防抖字数、XSS 净化、
 *      撤销/重做按钮状态、视觉行号渲染）
 *
 * 运行：npm test  (vitest run)
 * 依赖：jsdom 环境（vite.config.ts 已配置）
 */
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { ref, nextTick } from 'vue'
import EditorPanel from '@/components/workspace/EditorPanel.vue'
import { useWordCount } from '@/composables/useWordCount'
import { useChapterStore } from '@/stores/chapter'

function makeChapter(content: string) {
  return {
    id: '1',
    novel_id: '1',
    number: 1,
    title: '测试章节',
    outline: '',
    content,
    status: 'draft',
    word_count: 0,
    tension_score: 0,
    created_at: '',
    updated_at: '',
  } as any
}

describe('写作功能测试项目 / WritingFeature', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  describe('A. 字数统计 useWordCount', () => {
    it('A1 纯函数：中文字符逐个计数', () => {
      const { countWords } = useWordCount(ref(null))
      expect(countWords('你好世界')).toBe(4)
    })

    it('A2 纯函数：英文按单词计数', () => {
      const { countWords } = useWordCount(ref(null))
      expect(countWords('hello world foo')).toBe(3)
    })

    it('A3 纯函数：中英文混合 = 中文字数 + 英文单词数', () => {
      const { countWords } = useWordCount(ref(null))
      expect(countWords('你好 world 测试 foo')).toBe(4 + 2)
    })

    it('A4 纯函数：空字符串返回 0', () => {
      const { countWords } = useWordCount(ref(null))
      expect(countWords('')).toBe(0)
    })

    it('A5 立即更新路径：调用 updateWordCount 后同步得到结果（无定时器）', () => {
      const editorMock = { value: { getText: () => '你好world' } as any }
      const { wordCount, updateWordCount } = useWordCount(ref(null), editorMock)
      updateWordCount()
      // '你好'(2) + 'world'(1) = 3 —— 立即路径，不应有任何延迟
      expect(wordCount.value).toBe(3)
    })

    it('A6 防抖更新路径（B14）：未到 250ms 不更新，到点后更新', () => {
      vi.useFakeTimers()
      try {
        const editorMock = { value: { getText: () => '测试内容hello' } as any }
        const { wordCount, updateWordCountDebounced } = useWordCount(ref(null), editorMock)

        updateWordCountDebounced()
        // 尚未到防抖窗口
        expect(wordCount.value).toBe(0)

        vi.advanceTimersByTime(260)
        // '测试内容'(4) + 'hello'(1) = 5
        expect(wordCount.value).toBe(5)
      } finally {
        vi.useRealTimers()
      }
    })
  })

  describe('B. EditorPanel 组件集成', () => {
    it('B1 挂载后渲染写作工具栏与字数显示', async () => {
      const wrapper = mount(EditorPanel)
      await nextTick()
      expect(wrapper.find('.word-count').exists()).toBe(true)
      expect(wrapper.text()).toContain('AI 续写')
    })

    it('B2 章节切换（加载）后即时显示正确字数（立即路径，非防抖）', async () => {
      const chapterStore = useChapterStore()
      chapterStore.currentChapter = makeChapter('<p>你好世界</p>')

      const wrapper = mount(EditorPanel)
      await nextTick()
      await nextTick()

      // 章节加载走 watch → nextTick 内 updateWordCount()（立即），应为 4
      expect(wrapper.find('.word-count').text()).toContain('4')
    })

    it('B3 打字（emitUpdate）触发防抖：到点前仍为旧值，到点后更新为 6', async () => {
      const wrapper = mount(EditorPanel)
      await nextTick()
      const vm = wrapper.vm as any

      vm.editor.commands.setContent('<p>你好世界hello world</p>', true)
      // 防抖未触发时，字数仍是挂载时的 0
      expect(wrapper.find('.word-count').text()).toContain('0')

      // 等待防抖窗口（250ms）+ 渲染
      await new Promise((r) => setTimeout(r, 350))
      await nextTick()

      // '你好世界'(4) + 'hello'(1) + 'world'(1) = 6
      expect(wrapper.find('.word-count').text()).toContain('6')
    })

    it('B4 XSS 净化：恶意脚本/事件属性被过滤', async () => {
      const chapterStore = useChapterStore()
      chapterStore.currentChapter = makeChapter(
        '<p>正常内容</p><script>alert(1)</script><img src=x onerror="alert(1)">',
      )

      const wrapper = mount(EditorPanel)
      await nextTick()
      await nextTick()
      const vm = wrapper.vm as any
      const html = vm.editor ? vm.editor.getHTML() : ''
      expect(html).not.toContain('<script>')
      expect(html).not.toContain('onerror')
      expect(html).toContain('正常内容')
    })

    it('B5 撤销按钮：初始禁用，输入内容后可点击', async () => {
      const wrapper = mount(EditorPanel)
      await nextTick()
      const undoBtn = wrapper.find('[aria-label="撤销"]')
      expect(undoBtn.attributes('disabled')).toBeDefined()

      const vm = wrapper.vm as any
      vm.editor.commands.setContent('<p>第一章开始了</p>', true)
      await nextTick()
      await nextTick()

      const undoBtn2 = wrapper.find('[aria-label="撤销"]')
      // 输入后历史栈有记录，按钮应可用
      expect(undoBtn2.attributes('disabled')).toBeUndefined()
    })

    it('B6 视觉行号：至少渲染 MIN_LINES(99) 行占位（jsdom 下回落到默认行高）', async () => {
      const wrapper = mount(EditorPanel)
      await nextTick()
      const lineNumbers = wrapper.findAll('.line-number')
      expect(lineNumbers.length).toBeGreaterThanOrEqual(99)
    })
  })
})
