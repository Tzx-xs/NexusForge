<template>
  <div v-if="historyStore.visible" class="history-modal" @click.self="historyStore.close()">
    <div class="modal-content">
      <div class="modal-header">
        <h3 class="modal-title">
          历史快照
          <span v-if="historyStore.currentChapterId" class="chapter-tag">
            章节 #{{ historyStore.currentChapterId }}
          </span>
        </h3>
        <button class="close-btn" @click="historyStore.close()">×</button>
      </div>

      <div v-if="historyStore.loading" class="loading-state">加载中…</div>

      <div v-else-if="historyStore.snapshots.length === 0" class="empty-state">
        <p>暂无历史快照</p>
      </div>

      <div v-else class="snapshot-list">
        <div
          v-for="snap in sortedSnapshots"
          :key="snap.id"
          class="snapshot-item"
        >
          <div class="snap-header">
            <span class="snap-name">{{ snap.name || '未命名快照' }}</span>
            <span v-if="snap.snapshot_type" class="snap-type" :class="`type-${snap.snapshot_type}`">
              {{ snap.snapshot_type }}
            </span>
          </div>
          <p v-if="snap.description" class="snap-desc">{{ snap.description }}</p>
          <div class="snap-meta">
            <span v-if="snap.created_by" class="meta-item">由 {{ snap.created_by }}</span>
            <span class="meta-item">{{ formatTime(snap.created_at) }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useHistoryStore } from '@/stores/history'

const historyStore = useHistoryStore()

// 按 created_at 倒序展示
const sortedSnapshots = computed(() => {
  return [...historyStore.snapshots].sort((a, b) => {
    const ta = a.created_at ? Date.parse(a.created_at) : 0
    const tb = b.created_at ? Date.parse(b.created_at) : 0
    return tb - ta
  })
})

function formatTime(iso: string): string {
  if (!iso) return ''
  try {
    const d = new Date(iso)
    return `${d.getFullYear()}/${d.getMonth() + 1}/${d.getDate()} ${String(d.getHours()).padStart(2, '0')}:${String(d.getMinutes()).padStart(2, '0')}`
  } catch {
    return iso
  }
}
</script>

<style scoped>
.history-modal {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 80px;
  z-index: 1000;
}

.modal-content {
  width: 560px;
  max-width: 90vw;
  max-height: 70vh;
  background: var(--xy-surface-1);
  border: 1px solid var(--xy-border-1);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.3);
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid var(--xy-border-1);
}

.modal-title {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: var(--xy-text-1);
  display: flex;
  align-items: center;
  gap: 8px;
}

.chapter-tag {
  font-size: 11px;
  color: var(--xy-text-3);
  padding: 2px 8px;
  border-radius: 4px;
  background: var(--xy-surface-2);
  font-weight: 400;
}

.close-btn {
  border: none;
  background: transparent;
  color: var(--xy-text-3);
  font-size: 24px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
}

.close-btn:hover {
  background: var(--xy-surface-hover);
  color: var(--xy-text-1);
}

.loading-state,
.empty-state {
  padding: 32px;
  text-align: center;
  color: var(--xy-text-3);
  font-size: 13px;
}

.snapshot-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}

.snapshot-item {
  padding: 12px 16px;
  border-bottom: 1px solid var(--xy-border-1);
  cursor: pointer;
  transition: background 0.15s ease;
}

.snapshot-item:last-child {
  border-bottom: none;
}

.snapshot-item:hover {
  background: var(--xy-surface-hover);
}

.snap-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 4px;
}

.snap-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--xy-text-1);
}

.snap-type {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 3px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.snap-type.type-auto {
  background: rgba(59, 130, 246, 0.15);
  color: rgb(59, 130, 246);
}

.snap-type.type-manual {
  background: rgba(16, 185, 129, 0.15);
  color: rgb(16, 185, 129);
}

.snap-desc {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--xy-text-2);
  line-height: 1.5;
}

.snap-meta {
  margin-top: 4px;
  display: flex;
  gap: 12px;
  font-size: 11px;
  color: var(--xy-text-4);
}
</style>
