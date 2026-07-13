import { defineStore } from 'pinia'
import { ref } from 'vue'
import { searchAll, type SearchResults } from '@/api/search'

const EMPTY_RESULTS: SearchResults = {
  characters: [],
  foreshadows: [],
  facts: [],
  settings: [],
  chapters: [],
}

export const useSearchStore = defineStore('search', () => {
  const query = ref('')
  const results = ref<SearchResults>({ ...EMPTY_RESULTS })
  const loading = ref(false)
  const visible = ref(false)

  async function search(q: string, novelId: string) {
    if (!q?.trim()) {
      results.value = { ...EMPTY_RESULTS }
      return
    }
    loading.value = true
    try {
      const data = await searchAll(q, novelId)
      results.value = data
    } catch (err) {
      // 异常被捕获并保持 results 原值，不冒泡（避免触发 http.ts 的 toast）
      // 但 http.ts 的响应拦截器可能已经触发 toast，这里仅防止状态错乱
      // 不重置 results，保持原值供用户参考
      console.error('[searchStore] search failed:', err)
    } finally {
      loading.value = false
    }
  }

  function clear() {
    query.value = ''
    results.value = { ...EMPTY_RESULTS }
  }

  function open() {
    visible.value = true
  }

  function close() {
    visible.value = false
    query.value = ''
    results.value = { ...EMPTY_RESULTS }
  }

  return {
    query,
    results,
    loading,
    visible,
    search,
    clear,
    open,
    close,
  }
})
