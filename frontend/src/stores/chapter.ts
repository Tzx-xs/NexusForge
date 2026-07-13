import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  getChapterList,
  getChapter,
  createChapter as apiCreateChapter,
  updateChapter as apiUpdateChapter,
  deleteChapter as apiDeleteChapter,
  type Chapter,
} from '@/api/chapters'
import type { AxiosRequestConfig } from 'axios'

export const useChapterStore = defineStore('chapter', () => {
  const chapters = ref<Chapter[]>([])
  const currentChapter = ref<Chapter | null>(null)
  const loading = ref(false)
  let fetchChapterVersion = 0
  let fetchChaptersVersion = 0
  let lastFetchChaptersTime = 0
  let lastFetchChaptersNovelId = ''
  const CACHE_TTL = 60_000

  async function fetchChapters(novelId: string, options?: AxiosRequestConfig & { force?: boolean }) {
    const myVersion = ++fetchChaptersVersion
    const { force, ...config } = options || {}

    if (
      !force &&
      lastFetchChaptersNovelId === novelId &&
      Date.now() - lastFetchChaptersTime < CACHE_TTL &&
      chapters.value.length > 0
    ) {
      return
    }

    loading.value = true
    try {
      const data = await getChapterList(novelId, config)
      if (myVersion !== fetchChaptersVersion) return
      chapters.value = data
      lastFetchChaptersTime = Date.now()
      lastFetchChaptersNovelId = novelId
    } catch (e) {
      if (myVersion !== fetchChaptersVersion) return
      console.error('Failed to fetch chapters:', e)
      // 仅在首次加载（chapters 为空）时清空，网络波动时保留旧数据（MNT-L1）
      if (chapters.value.length === 0) {
        chapters.value = []
      }
    } finally {
      if (myVersion === fetchChaptersVersion) {
        loading.value = false
      }
    }
  }

  async function fetchChapter(chapterId: string, config?: AxiosRequestConfig) {
    const myVersion = ++fetchChapterVersion
    try {
      const data = await getChapter(chapterId, config)
      if (myVersion !== fetchChapterVersion) return null
      currentChapter.value = data
      return data
    } catch (e) {
      if (myVersion !== fetchChapterVersion) return null
      console.error('Failed to fetch chapter:', e)
      return null
    }
  }

  async function createChapter(novelId: string, data: { title: string; number?: number }) {
    const result = await apiCreateChapter(novelId, data)
    chapters.value.push(result)
    return result
  }

  async function updateChapter(chapterId: string, data: Partial<Chapter>) {
    const result = await apiUpdateChapter(chapterId, data)
    const index = chapters.value.findIndex((c) => c.id === chapterId)
    if (index !== -1) {
      chapters.value[index] = result
    }
    if (currentChapter.value?.id === chapterId) {
      currentChapter.value = result
    }
    return result
  }

  async function deleteChapter(chapterId: string) {
    await apiDeleteChapter(chapterId)
    chapters.value = chapters.value.filter((c) => c.id !== chapterId)
  }

  function selectChapter(chapterId: string) {
    const chapter = chapters.value.find((c) => c.id === chapterId)
    if (chapter) {
      currentChapter.value = chapter
    }
  }

  return {
    chapters,
    currentChapter,
    loading,
    fetchChapters,
    fetchChapter,
    createChapter,
    updateChapter,
    deleteChapter,
    selectChapter,
  }
})
