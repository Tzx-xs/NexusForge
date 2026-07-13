import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

// Mock search API 模块（store 尚未实现时也要先 mock，否则 import 失败）
vi.mock('@/api/search', () => ({
  searchAll: vi.fn(),
}))

import { searchAll } from '@/api/search'
import { useSearchStore } from '@/stores/search'

const EMPTY_RESULTS = {
  characters: [],
  foreshadows: [],
  facts: [],
  settings: [],
  chapters: [],
}

const MOCK_RESULTS = {
  characters: [{ id: 'c1', name: '唐凌轩', role: '主角', description: '少年' }],
  foreshadows: [{ id: 'f1', title: '星渊之力', description: '神秘力量', priority: 'P1', status: 'open' }],
  facts: [{ id: 'm1', fact_type: 'world', key: '年代', value: '2026' }],
  settings: [{ id: 'w1', name: '云栖书院', setting_type: 'location', description: '山门所在' }],
  chapters: [{ id: 'ch1', number: 1, title: '第一章', outline: '', status: 'draft', word_count: 0 }],
}

describe('Search Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('初始状态：query 为空、results 五类均为空数组、loading 为 false、visible 为 false', () => {
    const store = useSearchStore()

    expect(store.query).toBe('')
    expect(store.results).toEqual(EMPTY_RESULTS)
    expect(store.loading).toBe(false)
    expect(store.visible).toBe(false)
  })

  it('search 调用 searchAll API 并填充 results', async () => {
    vi.mocked(searchAll).mockResolvedValue(MOCK_RESULTS as any)

    const store = useSearchStore()
    await store.search('唐', 'n1')

    expect(searchAll).toHaveBeenCalledWith('唐', 'n1')
    expect(store.results).toEqual(MOCK_RESULTS)
    expect(store.loading).toBe(false)
  })

  it('search 期间 loading 为 true', async () => {
    let resolveFn: (v: any) => void = () => {}
    vi.mocked(searchAll).mockReturnValue(
      new Promise((resolve) => {
        resolveFn = resolve
      }) as any
    )

    const store = useSearchStore()
    const promise = store.search('唐', 'n1')

    expect(store.loading).toBe(true)

    resolveFn(MOCK_RESULTS)
    await promise

    expect(store.loading).toBe(false)
  })

  it('search 完成后 loading 为 false', async () => {
    vi.mocked(searchAll).mockResolvedValue(MOCK_RESULTS as any)

    const store = useSearchStore()
    await store.search('唐', 'n1')

    expect(store.loading).toBe(false)
  })

  it('clear 清空 query 和 results', async () => {
    vi.mocked(searchAll).mockResolvedValue(MOCK_RESULTS as any)

    const store = useSearchStore()
    store.query = '残留关键词'
    await store.search('唐', 'n1')
    expect(store.results).toEqual(MOCK_RESULTS)

    store.clear()

    expect(store.query).toBe('')
    expect(store.results).toEqual(EMPTY_RESULTS)
  })

  it('open 设置 visible 为 true', () => {
    const store = useSearchStore()

    store.open()

    expect(store.visible).toBe(true)
  })

  it('close 设置 visible 为 false 并清空 query 和 results', async () => {
    vi.mocked(searchAll).mockResolvedValue(MOCK_RESULTS as any)

    const store = useSearchStore()
    store.open()
    store.query = '唐'
    await store.search('唐', 'n1')
    expect(store.visible).toBe(true)
    expect(store.results).toEqual(MOCK_RESULTS)

    store.close()

    expect(store.visible).toBe(false)
    expect(store.query).toBe('')
    expect(store.results).toEqual(EMPTY_RESULTS)
  })

  it('search 失败时 loading 为 false 且 results 保持原值（不冒泡到 http.ts toast）', async () => {
    vi.mocked(searchAll).mockResolvedValueOnce(MOCK_RESULTS as any)
    vi.mocked(searchAll).mockRejectedValueOnce(new Error('网络错误'))

    const store = useSearchStore()
    await store.search('唐', 'n1')
    expect(store.results).toEqual(MOCK_RESULTS)

    // 第二次搜索失败
    await store.search('凌', 'n1')

    expect(store.loading).toBe(false)
    // results 保持原值（不被清空）
    expect(store.results).toEqual(MOCK_RESULTS)
  })
})
