import { describe, it, expect } from 'vitest'
import { useWordCount } from '@/composables/useWordCount'
import { ref } from 'vue'

describe('useWordCount', () => {
  it('应该正确统计中文字符数', () => {
    const editorRef = ref<HTMLDivElement | null>(null)
    const { countWords } = useWordCount(editorRef)

    expect(countWords('你好世界')).toBe(4)
  })

  it('应该正确统计英文单词数', () => {
    const editorRef = ref<HTMLDivElement | null>(null)
    const { countWords } = useWordCount(editorRef)

    expect(countWords('hello world foo')).toBe(3)
  })

  it('应该正确统计中英文混合内容', () => {
    const editorRef = ref<HTMLDivElement | null>(null)
    const { countWords } = useWordCount(editorRef)

    expect(countWords('你好 world 测试 foo')).toBe(4 + 2)
  })

  it('空字符串应该返回 0', () => {
    const editorRef = ref<HTMLDivElement | null>(null)
    const { countWords } = useWordCount(editorRef)

    expect(countWords('')).toBe(0)
  })
})
