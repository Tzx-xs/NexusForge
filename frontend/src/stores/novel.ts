import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  getNovelList,
  createNovel as apiCreateNovel,
  deleteNovel as apiDeleteNovel,
  updateNovel as apiUpdateNovel,
  getNovelStats,
  type Novel,
  type NovelStats,
  type NovelListResult,
} from '@/api/novels'
import type { AxiosRequestConfig } from 'axios'

export interface NovelWithStats extends Novel {
  word_count?: string
  stats?: NovelStats
}

export const useNovelStore = defineStore('novel', () => {
  const novels = ref<NovelWithStats[]>([])
  const total = ref(0)
  const loading = ref(false)
  const pageSize = ref(12)
  let lastFetchTime = 0
  let lastFetchedPage = 1
  const CACHE_TTL = 60_000

  function formatWordCount(n: number): string {
    if (n >= 10000) return `${(n / 10000).toFixed(1)}万字`
    if (n >= 1000) return `${(n / 1000).toFixed(1)}千字`
    return `${n}字`
  }

  async function fetchStatsForPage(items: NovelWithStats[]) {
    const CONCURRENCY = 5
    const tasks = items.map((novel, index) => async () => {
      try {
        const stats = await getNovelStats(novel.id)
        items[index].stats = stats
        items[index].word_count = formatWordCount(stats.total_words)
      } catch (e) {
        console.warn('Failed to fetch novel stats:', e)
      }
    })

    let cursor = 0
    const workers = Array.from({ length: Math.min(CONCURRENCY, tasks.length) }, async () => {
      while (cursor < tasks.length) {
        const i = cursor++
        await tasks[i]()
      }
    })
    await Promise.all(workers)
  }

  async function fetchNovels(options?: { force?: boolean; page?: number }) {
    const page = options?.page ?? 1
    if (
      !options?.force &&
      lastFetchTime > 0 &&
      Date.now() - lastFetchTime < CACHE_TTL &&
      novels.value.length > 0 &&
      lastFetchedPage === page
    ) {
      return
    }
    loading.value = true
    try {
      const data = await getNovelList({ page, page_size: pageSize.value })
      const list = normalizeListResponse(data)
      novels.value = list.items.map((novel) => ({ ...novel, word_count: '-' }))
      total.value = list.total
      fetchStatsForPage(novels.value)
      lastFetchedPage = page
      lastFetchTime = Date.now()
    } catch (e) {
      console.error('Failed to fetch novels:', e)
    } finally {
      loading.value = false
    }
  }

  function normalizeListResponse(data: NovelListResult | Novel[]): NovelListResult {
    if (Array.isArray(data)) {
      return {
        items: data,
        total: data.length,
        page: 1,
        page_size: data.length,
      }
    }
    return data
  }

  async function createNovel(
    data: {
      title: string
      premise: string
      genre: string
      target_chapters: number
      style_tags?: string[]
      perspective?: string
      cover_url?: string
    },
    config?: AxiosRequestConfig
  ) {
    const result = await apiCreateNovel(data, config)
    novels.value.unshift({ ...result, word_count: '-' })
    total.value += 1
    return result
  }

  async function deleteNovel(id: string, config?: AxiosRequestConfig) {
    await apiDeleteNovel(id, config)
    novels.value = novels.value.filter((n) => n.id !== id)
    total.value = Math.max(0, total.value - 1)
  }

  async function updateNovel(id: string, data: Partial<Novel>) {
    const result = await apiUpdateNovel(id, data)
    const index = novels.value.findIndex((n) => n.id === id)
    if (index >= 0) {
      novels.value[index] = { ...novels.value[index], ...result }
    }
    return result
  }

  return {
    novels,
    total,
    loading,
    pageSize,
    fetchNovels,
    createNovel,
    deleteNovel,
    updateNovel,
  }
})
