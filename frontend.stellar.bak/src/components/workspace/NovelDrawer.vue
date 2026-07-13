<template>
  <XyDrawer
    v-model="isVisible"
    placement="right"
    :width="drawerWidth"
    :title="novelTitle"
    @close="handleClose"
  >
    <div class="novel-drawer-content">
      <div class="novel-drawer-header-info">
        <div class="novel-meta">
          <span class="meta-item">{{ chapterCount }} 章</span>
          <span class="meta-divider">·</span>
          <span class="meta-item">{{ wordCount }} 字</span>
        </div>
      </div>

      <div class="novel-drawer-layout">
        <aside class="novel-sidebar">
          <WritingSidebar />
        </aside>

        <main class="novel-editor-area">
          <EditorPanel />
        </main>

        <aside class="novel-file-panel">
          <FileViewer
            v-if="docViewerStore.hasSelection"
            :title="docViewerStore.title"
            :content="docViewerStore.content"
            :mode="docViewerStore.mode"
          />
          <div v-else class="file-panel-empty">
            <FileText class="empty-icon" />
            <span class="empty-text">选择章节或设定查看</span>
          </div>
        </aside>
      </div>
    </div>
  </XyDrawer>
</template>

<script setup lang="ts">
import { computed, watch, onUnmounted } from 'vue'
import { FileText } from '@vicons/tabler'
import { useNovelStore } from '@/stores/novel'
import { useChapterStore } from '@/stores/chapter'
import { useDocViewerStore } from '@/stores/docViewer'
import { useBibleStore } from '@/stores/bible'
import XyDrawer from '@/components/common/XyDrawer.vue'
import WritingSidebar from './WritingSidebar.vue'
import EditorPanel from './EditorPanel.vue'
import FileViewer from './FileViewer.vue'

const props = defineProps<{
  visible: boolean
  novelId: string
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  close: []
}>()

const novelStore = useNovelStore()
const chapterStore = useChapterStore()
const docViewerStore = useDocViewerStore()
const bibleStore = useBibleStore()

const isVisible = computed({
  get: () => props.visible,
  set: (value) => emit('update:visible', value)
})

const novelTitle = computed(() => {
  const novel = novelStore.novels.find(n => n.id === props.novelId)
  return novel?.title || ''
})

const chapterCount = computed(() => chapterStore.chapters.length)

const wordCount = computed(() => {
  return chapterStore.chapters.reduce((sum, ch) => sum + (ch.content?.length || 0), 0)
})

const drawerWidth = computed(() => {
  const screenWidth = window.innerWidth
  if (screenWidth < 1024) return '100vw'
  if (screenWidth < 1440) return '900px'
  return '1100px'
})

let abortController: AbortController | null = null

function cancelPendingRequests() {
  if (abortController) {
    abortController.abort()
    abortController = null
  }
}

async function loadNovelData() {
  if (!props.novelId) return
  
  cancelPendingRequests()
  abortController = new AbortController()

  await chapterStore.fetchChapters(props.novelId, { signal: abortController?.signal })
  await bibleStore.fetchCharacters(props.novelId)
  await bibleStore.fetchSettings(props.novelId)

  if (chapterStore.chapters.length > 0) {
    const firstChapter = chapterStore.chapters[0]
    chapterStore.currentChapter = firstChapter
    docViewerStore.selectChapter(firstChapter)
    await chapterStore.fetchChapter(firstChapter.id, { signal: abortController?.signal })
  }
}

function handleClose() {
  cancelPendingRequests()
  emit('close')
}

watch(
  () => props.visible,
  async (visible) => {
    if (visible) {
      await loadNovelData()
    } else {
      cancelPendingRequests()
    }
  },
  { immediate: true }
)

watch(
  () => props.novelId,
  () => {
    if (props.visible) {
      loadNovelData()
    }
  }
)

onUnmounted(() => {
  cancelPendingRequests()
})
</script>

<style scoped>
.novel-drawer-content {
  display: flex;
  flex-direction: column;
  height: calc(100vh - var(--xy-panel-header-h));
  overflow: hidden;
}

.novel-drawer-header-info {
  flex-shrink: 0;
  padding: var(--xy-space-3) var(--xy-space-4);
  border-bottom: var(--xy-border-w-1) solid var(--xy-divider);
  background: var(--xy-surface-2);
}

.novel-meta {
  display: flex;
  align-items: center;
  gap: var(--xy-space-2);
  color: var(--xy-text-3);
  font-size: var(--xy-fs-xs);
}

.meta-item {
  display: flex;
  align-items: center;
}

.meta-divider {
  opacity: 0.4;
}

.novel-drawer-layout {
  flex: 1;
  display: flex;
  min-height: 0;
}

.novel-sidebar {
  flex: 0 0 280px;
  border-right: var(--xy-border-w-1) solid var(--xy-split-border);
  overflow: hidden;
}

.novel-editor-area {
  flex: 1;
  min-width: 0;
  overflow: hidden;
}

.novel-file-panel {
  flex: 0 0 320px;
  border-left: var(--xy-border-w-1) solid var(--xy-split-border);
  background: var(--xy-surface-1);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.file-panel-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--xy-space-3);
  color: var(--xy-text-4);
}

.empty-icon {
  width: 48px;
  height: 48px;
  opacity: 0.3;
}

.empty-text {
  font-size: var(--xy-fs-xs);
}

@media (max-width: 1024px) {
  .novel-sidebar {
    flex: 0 0 240px;
  }
  
  .novel-file-panel {
    flex: 0 0 280px;
  }
}

@media (max-width: 768px) {
  .novel-sidebar {
    display: none;
  }
  
  .novel-file-panel {
    flex: 0 0 240px;
  }
}
</style>