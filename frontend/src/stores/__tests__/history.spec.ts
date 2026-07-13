import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import type { Snapshot } from '@/api/snapshots'

// Mock snapshots API（复用既有 listSnapshots / listChapterSnapshots）
vi.mock('@/api/snapshots', () => ({
  listSnapshots: vi.fn(),
  listChapterSnapshots: vi.fn(),
}))

import { listSnapshots } from '@/api/snapshots'
import { useHistoryStore } from '@/stores/history'

const MOCK_SNAPSHOTS: Snapshot[] = [
  {
    id: 's1',
    novel_id: 'n1',
    chapter_id: 'c1',
    snapshot_type: 'manual',
    name: '第一章初稿',
    description: '初版',
    created_by: 'user',
    created_at: '2026-07-01T10:00:00Z',
    updated_at: '2026-07-01T10:00:00Z',
  },
  {
    id: 's2',
    novel_id: 'n1',
    chapter_id: 'c1',
    snapshot_type: 'auto',
    name: '自动保存',
    description: '',
    created_by: 'system',
    created_at: '2026-07-02T15:30:00Z',
    updated_at: '2026-07-02T15:30:00Z',
  },
]

describe('History Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  it('初始状态：snapshots 为空数组、loading 为 false、visible 为 false、currentChapterId 为 null', () => {
    const store = useHistoryStore()

    expect(store.snapshots).toEqual([])
    expect(store.loading).toBe(false)
    expect(store.visible).toBe(false)
    expect(store.currentChapterId).toBeNull()
  })

  it('fetchSnapshots(novelId) 调用 listSnapshots API 并填充 snapshots', async () => {
    vi.mocked(listSnapshots).mockResolvedValue(MOCK_SNAPSHOTS as any)

    const store = useHistoryStore()
    await store.fetchSnapshots('n1')

    expect(listSnapshots).toHaveBeenCalledWith('n1', { limit: 50 })
    expect(store.snapshots).toEqual(MOCK_SNAPSHOTS)
    expect(store.loading).toBe(false)
  })

  it('fetchSnapshots 期间 loading 为 true', async () => {
    let resolveFn: (v: any) => void = () => {}
    vi.mocked(listSnapshots).mockReturnValue(
      new Promise((resolve) => {
        resolveFn = resolve
      }) as any
    )

    const store = useHistoryStore()
    const promise = store.fetchSnapshots('n1')

    expect(store.loading).toBe(true)

    resolveFn(MOCK_SNAPSHOTS)
    await promise

    expect(store.loading).toBe(false)
  })

  it('fetchSnapshots 完成后 loading 为 false', async () => {
    vi.mocked(listSnapshots).mockResolvedValue(MOCK_SNAPSHOTS as any)

    const store = useHistoryStore()
    await store.fetchSnapshots('n1')

    expect(store.loading).toBe(false)
  })

  it('open(chapterId, novelId) 设置 visible 为 true 并触发 fetchSnapshots', async () => {
    vi.mocked(listSnapshots).mockResolvedValue(MOCK_SNAPSHOTS as any)

    const store = useHistoryStore()
    await store.open('c1', 'n1')

    expect(store.visible).toBe(true)
    expect(store.currentChapterId).toBe('c1')
    expect(store.snapshots).toEqual(MOCK_SNAPSHOTS)
    expect(listSnapshots).toHaveBeenCalledWith('n1', { chapter_id: 'c1', limit: 50 })
  })

  it('open 时不传 chapterId 则 currentChapterId 仍为 null', async () => {
    vi.mocked(listSnapshots).mockResolvedValue(MOCK_SNAPSHOTS as any)

    const store = useHistoryStore()
    await store.open(undefined, 'n1')

    expect(store.visible).toBe(true)
    expect(store.currentChapterId).toBeNull()
  })

  it('close 设置 visible 为 false 并清空 snapshots 与 currentChapterId', async () => {
    vi.mocked(listSnapshots).mockResolvedValue(MOCK_SNAPSHOTS as any)

    const store = useHistoryStore()
    await store.open('c1', 'n1')
    expect(store.snapshots).toHaveLength(2)

    store.close()

    expect(store.visible).toBe(false)
    expect(store.snapshots).toEqual([])
    expect(store.currentChapterId).toBeNull()
  })

  it('fetchSnapshots 失败时 loading 为 false 且 snapshots 保持原值（不冒泡到 http.ts toast）', async () => {
    vi.mocked(listSnapshots).mockResolvedValueOnce(MOCK_SNAPSHOTS as any)
    vi.mocked(listSnapshots).mockRejectedValueOnce(new Error('网络错误'))

    const store = useHistoryStore()
    await store.fetchSnapshots('n1')
    expect(store.snapshots).toEqual(MOCK_SNAPSHOTS)

    // 第二次 fetch 失败
    await store.fetchSnapshots('n1')

    expect(store.loading).toBe(false)
    // snapshots 保持原值（不被清空）
    expect(store.snapshots).toEqual(MOCK_SNAPSHOTS)
  })
})
