import { defineStore } from 'pinia'
import { ref } from 'vue'
import { listSnapshots, type Snapshot } from '@/api/snapshots'

export const useHistoryStore = defineStore('history', () => {
  const snapshots = ref<Snapshot[]>([])
  const loading = ref(false)
  const visible = ref(false)
  const currentChapterId = ref<string | null>(null)
  const currentNovelId = ref<string | null>(null)

  async function fetchSnapshots(novelId: string, chapterId?: string) {
    loading.value = true
    try {
      const list = await listSnapshots(
        novelId,
        chapterId ? { limit: 50, chapter_id: chapterId } : { limit: 50 }
      )
      snapshots.value = list
    } catch (err) {
      // 异常被捕获并保持 snapshots 原值
      console.error('[historyStore] fetchSnapshots failed:', err)
    } finally {
      loading.value = false
    }
  }

  async function open(chapterId?: string | null, novelId?: string) {
    if (chapterId) {
      currentChapterId.value = chapterId
    } else {
      currentChapterId.value = null
    }
    if (novelId) {
      currentNovelId.value = novelId
      await fetchSnapshots(novelId, chapterId ?? undefined)
    }
    visible.value = true
  }

  function close() {
    visible.value = false
    snapshots.value = []
    currentChapterId.value = null
  }

  return {
    snapshots,
    loading,
    visible,
    currentChapterId,
    currentNovelId,
    fetchSnapshots,
    open,
    close,
  }
})
