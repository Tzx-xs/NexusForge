<template>
  <div class="empty-state">
    <NexusLogo size="xl" :is-rotating="true" />
    <h2 class="empty-title">欢迎使用 Nexus</h2>
    <p class="empty-subtitle">离线优先的个人知识管理工具</p>
    <div class="empty-actions">
      <button class="empty-btn primary" @click="createNote">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M12 5v14M5 12h14" />
        </svg>
        新建笔记
      </button>
      <button class="empty-btn" @click="openImport">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
          <polyline points="7 10 12 15 17 10" />
          <line x1="12" y1="15" x2="12" y2="3" />
        </svg>
        导入 Markdown
      </button>
    </div>
    <p class="empty-hint">按 <kbd>⌘K</kbd> 打开命令面板</p>
  </div>
</template>

<script setup lang="ts">
import NexusLogo from '../icons/NexusLogo.vue'

function createNote() {
  // TODO: Phase 3
  console.log('createNote')
}

function openImport() {
  // TODO: Phase 5
  console.log('openImport')
}
</script>

<style scoped>
.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  padding: 40px;
  text-align: center;
}
.empty-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--nexus-text);
  margin: 0;
}
.empty-subtitle {
  font-size: 14px;
  color: var(--nexus-text-secondary);
  margin: 0;
}
.empty-actions {
  display: flex;
  gap: 12px;
  margin-top: 8px;
}
.empty-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border: 1px solid var(--nexus-border);
  background: var(--nexus-surface);
  color: var(--nexus-text-secondary);
  border-radius: var(--nexus-radius-md);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s ease;
}
.empty-btn:hover {
  background: var(--nexus-bg-hover);
  color: var(--nexus-text);
  border-color: var(--nexus-border-hover);
}
.empty-btn.primary {
  background: var(--nexus-accent);
  border-color: var(--nexus-accent);
  color: #fff;
}
.empty-btn.primary:hover {
  background: var(--nexus-accent-hover);
}
.empty-hint {
  font-size: 12px;
  color: var(--nexus-text-tertiary);
  margin-top: 16px;
}
.empty-hint kbd {
  padding: 2px 6px;
  background: var(--nexus-bg);
  border: 1px solid var(--nexus-border);
  border-radius: 4px;
  font-family: inherit;
  font-size: 11px;
}
</style>
