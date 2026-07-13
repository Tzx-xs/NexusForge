import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useNovelStore } from '@/stores/novel'

export function useCurrentNovelId() {
  const route = useRoute()
  const novelStore = useNovelStore()

  const novelId = computed(() => {
    if (route.params.novelId) {
      return String(route.params.novelId)
    }
    const lastNovel = localStorage.getItem('xy-last-novel')
    if (lastNovel) {
      return lastNovel
    }
    if (novelStore.novels.length > 0) {
      return novelStore.novels[0].id
    }
    return '1'
  })

  return {
    novelId,
  }
}
