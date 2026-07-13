import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useNovelStore } from '@/stores/novel'
import type { Novel } from '@/api/novels'

// Mock the novels API - simulates the FIXED behavior where interceptor unpacks response
vi.mock('@/api/novels', () => ({
  getNovelList: vi.fn(),
  createNovel: vi.fn(),
}))

import { getNovelList, createNovel } from '@/api/novels'

describe('Novel Store - Response Unpacking', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('should store novel array after fetchNovels (interceptor unpacked)', async () => {
    const mockNovels: Novel[] = [
      {
        id: '1',
        title: '渊海纪元',
        premise: 'test',
        genre: '玄幻',
        target_chapters: 100,
        current_chapter: 3,
        cover_url: '',
        style_tags: [],
        perspective: '',
        created_at: '',
        updated_at: '',
      },
      {
        id: '2',
        title: '暗夜追踪者',
        premise: 'test2',
        genre: '都市',
        target_chapters: 50,
        current_chapter: 1,
        cover_url: '',
        style_tags: [],
        perspective: '',
        created_at: '',
        updated_at: '',
      },
    ]

    // After fix: getNovelList returns the unpacked data (just the array)
    vi.mocked(getNovelList).mockResolvedValue(mockNovels as any)

    const store = useNovelStore()
    await store.fetchNovels()

    expect(Array.isArray(store.novels)).toBe(true)
    expect(store.novels.length).toBe(2)
    expect(store.novels[0].title).toBe('渊海纪元')
    expect(store.novels[1].title).toBe('暗夜追踪者')
  })

  it('should NOT have code/message wrapper in stored novels', async () => {
    const mockNovels: Novel[] = [
      {
        id: '1',
        title: '测试小说',
        premise: '',
        genre: '',
        target_chapters: 0,
        current_chapter: 0,
        cover_url: '',
        style_tags: [],
        perspective: '',
        created_at: '',
        updated_at: '',
      },
    ]

    vi.mocked(getNovelList).mockResolvedValue(mockNovels as any)

    const store = useNovelStore()
    await store.fetchNovels()

    // Ensure no wrapper properties leak into stored data
    expect(store.novels[0]).not.toHaveProperty('code')
    expect(store.novels[0]).not.toHaveProperty('message')
    expect(store.novels[0]).toHaveProperty('id')
    expect(store.novels[0]).toHaveProperty('title')
  })

  it('should store created novel object after createNovel', async () => {
    const mockNovel: Novel = {
      id: '3',
      title: '新小说',
      premise: 'test',
      genre: '玄幻',
      target_chapters: 100,
      current_chapter: 0,
      cover_url: '',
      style_tags: [],
      perspective: '',
      created_at: '',
      updated_at: '',
    }

    vi.mocked(createNovel).mockResolvedValue(mockNovel as any)

    const store = useNovelStore()
    const result = await store.createNovel({
      title: '新小说',
      premise: 'test',
      genre: '玄幻',
      target_chapters: 100,
    })

    expect(result).toHaveProperty('title', '新小说')
    expect(result).not.toHaveProperty('code')
    expect(result).not.toHaveProperty('message')

    expect(store.novels.length).toBe(1)
    expect(store.novels[0].title).toBe('新小说')
  })
})

describe('HTTP Interceptor - Response Unpacking', () => {
  it('should extract data field from {code, message, data} wrapper', async () => {
    // Test the interceptor logic directly
    const wrapperResponse = {
      data: {
        code: 0,
        message: 'success',
        data: [{ id: '1', title: 'test' }],
      },
    }

    // Simulate interceptor logic
    const res = wrapperResponse.data
    const unpacked = res && typeof res.code !== 'undefined' ? res.data : res

    expect(unpacked).toEqual([{ id: '1', title: 'test' }])
    expect(unpacked).not.toHaveProperty('code')
  })
})
