<template>
  <footer class="status-bar">
    <div class="status-left">
      <span class="status-item" title="本地存储">
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <ellipse cx="12" cy="5" rx="9" ry="3" />
          <path d="M3 5v14c0 1.66 4.03 3 9 3s9-1.34 9-3V5" />
          <path d="M3 12c0 1.66 4.03 3 9 3s9-1.34 9-3" />
        </svg>
        <span>本地存储</span>
      </span>
      <span class="status-separator">·</span>
      <span class="status-item">
        <span>{{ noteCount }} 篇笔记</span>
      </span>
    </div>
    <div class="status-center">
      <span v-if="currentNote" class="status-item">
        <span>{{ wordCount }} 字</span>
      </span>
    </div>
    <div class="status-right">
      <span class="status-item">
        <span>v0.1.0</span>
      </span>
    </div>
  </footer>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useEditor } from '@/core'

const { state } = useEditor()

const noteCount = computed(() => state.value.filePath ? 1 : 0)
const wordCount = computed(() => {
  if (!state.value.content) return 0
  return state.value.content.replace(/\s/g, '').length
})
const currentNote = computed(() => state.value.filePath)
</script>

<style scoped>
.status-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 24px;
  padding: 0 12px;
  background: var(--nexus-surface);
  border-top: 1px solid var(--nexus-border);
  font-size: 11px;
  color: var(--nexus-text-tertiary);
  flex-shrink: 0;
  user-select: none;
}
.status-left,
.status-center,
.status-right {
  display: flex;
  align-items: center;
  gap: 6px;
}
.status-item {
  display: flex;
  align-items: center;
  gap: 4px;
}
.status-separator {
  color: var(--nexus-text-tertiary);
  opacity: 0.5;
}
</style>
