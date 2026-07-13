import { describe, it, expect, beforeEach, vi } from 'vitest'
import { useAutoSave } from '@/composables/useAutoSave'
import { ref } from 'vue'
import { createPinia, setActivePinia } from 'pinia'

describe('useAutoSave', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.useFakeTimers()
  })

  it('应该在延迟后调用 save 回调', () => {
    const editorRef = ref({ innerHTML: '<p>test</p>' } as unknown as HTMLDivElement)
    const chapter = { id: '1' }
    const updateChapter = vi.fn()

    const { saveContent } = useAutoSave(editorRef, () => chapter, updateChapter, 1000)

    saveContent()
    expect(updateChapter).not.toHaveBeenCalled()

    vi.advanceTimersByTime(500)
    expect(updateChapter).not.toHaveBeenCalled()

    vi.advanceTimersByTime(600)
    expect(updateChapter).toHaveBeenCalledTimes(1)
    expect(updateChapter).toHaveBeenCalledWith('1', { content: '<p>test</p>' })
  })

  it('应该防抖：多次调用只执行最后一次', () => {
    const editorRef = ref({ innerHTML: '<p>first</p>' } as unknown as HTMLDivElement)
    const chapter = { id: '1' }
    const updateChapter = vi.fn()

    const { saveContent } = useAutoSave(editorRef, () => chapter, updateChapter, 1000)

    saveContent()
    vi.advanceTimersByTime(500)

    editorRef.value = { innerHTML: '<p>second</p>' } as unknown as HTMLDivElement
    saveContent()

    vi.advanceTimersByTime(600)
    expect(updateChapter).not.toHaveBeenCalled()

    vi.advanceTimersByTime(500)
    expect(updateChapter).toHaveBeenCalledTimes(1)
    expect(updateChapter).toHaveBeenCalledWith('1', { content: '<p>second</p>' })
  })

  it('没有章节时不保存', () => {
    const editorRef = ref({ innerHTML: '<p>test</p>' } as unknown as HTMLDivElement)
    const updateChapter = vi.fn()

    const { saveContent } = useAutoSave(editorRef, () => null, updateChapter, 1000)

    saveContent()
    vi.advanceTimersByTime(2000)
    expect(updateChapter).not.toHaveBeenCalled()
  })
})
