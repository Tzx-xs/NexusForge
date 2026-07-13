<template>
  <div class="writing-page">
    <div class="split-layout">
      <EditorPanel class="writing-editor" />
      <div class="file-panel">
        <FileViewer
          :title="docViewerStore.title"
          :content="docViewerStore.content"
          :mode="docViewerStore.mode"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { watch, onBeforeUnmount, getCurrentScope, onScopeDispose } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { EditorPanel, FileViewer } from '@/components/workspace'
import { useChapterStore } from '@/stores/chapter'
import { useDocViewerStore } from '@/stores/docViewer'

const route = useRoute()
const router = useRouter()
const chapterStore = useChapterStore()
const docViewerStore = useDocViewerStore()

let abortController: AbortController | null = null

function cancelPendingRequests() {
  if (abortController) {
    abortController.abort()
    abortController = null
  }
}

async function resolveCurrentChapter(novelId: string, chapterId: string) {
  await chapterStore.fetchChapters(novelId, { signal: abortController?.signal })

  const chapters = chapterStore.chapters
  if (chapters.length === 0) {
    chapterStore.currentChapter = null
    docViewerStore.clear()
    return
  }

  // 优先按 ID 匹配
  let target = chapters.find((c) => c.id === chapterId)

  // 未命中则按章节号匹配（URL 占位符 "1" / "2" 等）
  if (!target && /^\d+$/.test(chapterId)) {
    const number = parseInt(chapterId, 10)
    target = chapters.find((c) => c.number === number)
  }

  // 仍未命中则回退到第一章
  if (!target) {
    target = chapters[0]
  }

  if (!target) return

  // 如果当前 URL 不是目标章节的真实 ID，重定向修正
  const targetRouteId = String(target.id)
  if (chapterId !== targetRouteId) {
    try {
      await router.replace({ name: 'writing', params: { novelId, chapterId: targetRouteId } })
    } catch (e) {
      console.warn('[WritingPage] redirect failed:', e)
    }
    return
  }

  chapterStore.currentChapter = target
  docViewerStore.selectChapter(target)
  await chapterStore.fetchChapter(targetRouteId, { signal: abortController?.signal })
}

watch(
  () => [route.params.novelId, route.params.chapterId],
  async ([nid, cid]) => {
    cancelPendingRequests()
    abortController = new AbortController()

    if (typeof nid === 'string' && typeof cid === 'string') {
      await resolveCurrentChapter(nid, cid)
    }
  },
  { immediate: true, flush: 'pre' }
)

onBeforeUnmount(() => {
  cancelPendingRequests()
})

if (getCurrentScope()) {
  onScopeDispose(() => {
    cancelPendingRequests()
  })
}
</script>

<style scoped>
.writing-page {
  display: flex;
  flex: 1 1 0;
  min-height: 0;
  width: 100%;
  overflow: hidden;
}

.split-layout {
  display: flex;
  width: 100%;
  height: 100%;
}

.writing-editor {
  flex: 1 1 0;
  min-width: 0;
}

.file-panel {
  flex: 0 0 380px;
  width: 380px;
  border-left: var(--xy-border-w-1) solid var(--xy-split-border);
  background: var(--xy-surface-1);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
</style>
