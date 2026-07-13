import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useChapterStore } from '@/stores/chapter'

vi.mock('@/api/chapters', () => ({
  getChapterList: vi.fn(),
  getChapter: vi.fn(),
  createChapter: vi.fn(),
  updateChapter: vi.fn(),
  deleteChapter: vi.fn(),
}))

import { getChapterList, getChapter } from '@/api/chapters'

describe('Chapter Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('应该初始化为空状态', () => {
    const store = useChapterStore()
    expect(store.chapters).toEqual([])
    expect(store.currentChapter).toBeNull()
    expect(store.loading).toBe(false)
  })

  it('fetchChapters 应该正确填充 chapters', async () => {
    const mockChapters = [
      {
        id: '1',
        title: '第一章',
        novel_id: 'n1',
        number: 1,
        content: '',
        outline: '',
        status: 'draft',
        word_count: 0,
        tension_score: 0,
        created_at: '',
        updated_at: '',
      },
    ]
    vi.mocked(getChapterList).mockResolvedValue(mockChapters as any)

    const store = useChapterStore()
    await store.fetchChapters('n1')

    expect(store.chapters).toHaveLength(1)
    expect(store.chapters[0].title).toBe('第一章')
    expect(store.loading).toBe(false)
  })

  it('fetchChapter 应该设置 currentChapter', async () => {
    const mockChapter = {
      id: 'c1',
      title: '测试章节',
      novel_id: 'n1',
      number: 1,
      content: '',
      outline: '',
      status: 'draft',
      word_count: 0,
      tension_score: 0,
      created_at: '',
      updated_at: '',
    }
    vi.mocked(getChapter).mockResolvedValue(mockChapter as any)

    const store = useChapterStore()
    const result = await store.fetchChapter('c1')

    expect(result).toEqual(mockChapter)
    expect(store.currentChapter?.id).toBe('c1')
  })

  it('fetchChapters 失败时应该清空 chapters', async () => {
    vi.mocked(getChapterList).mockRejectedValue(new Error('fail'))

    const store = useChapterStore()
    await store.fetchChapters('n1')

    expect(store.chapters).toEqual([])
  })
})
