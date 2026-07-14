<template>
  <div class="folder-panel">
    <div class="panel-header">
      <span class="panel-title">文件夹</span>
      <button class="panel-action" title="新建文件夹">
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M12 5v14M5 12h14" />
        </svg>
      </button>
    </div>
    <div class="folder-list">
      <div class="folder-item active">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M15 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7Z" />
          <path d="M14 2v4a2 2 0 0 0 2 2h4" />
        </svg>
        <span class="folder-name">所有笔记</span>
        <span class="folder-count">0</span>
      </div>
      <div class="folder-item">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z" />
        </svg>
        <span class="folder-name">收藏</span>
        <span class="folder-count">0</span>
      </div>
      <div class="folder-item">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M21 8v13H3V3h13" />
          <path d="m21 12-7-7" />
          <path d="M7 12h10" />
        </svg>
        <span class="folder-name">归档</span>
        <span class="folder-count">0</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
.folder-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}
.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
}
.panel-title {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--nexus-text-tertiary);
}
.panel-action {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  border: none;
  background: transparent;
  color: var(--nexus-text-tertiary);
  border-radius: var(--nexus-radius-sm);
  cursor: pointer;
}
.panel-action:hover {
  background: var(--nexus-bg-hover);
  color: var(--nexus-text);
}
.folder-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 8px;
}
.folder-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: var(--nexus-radius-sm);
  cursor: pointer;
  color: var(--nexus-text-secondary);
  font-size: 13px;
  transition: background 0.1s ease;
}
.folder-item:hover {
  background: var(--nexus-bg-hover);
}
.folder-item.active {
  background: var(--nexus-bg-active);
  color: var(--nexus-text);
}
.folder-name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.folder-count {
  font-size: 11px;
  color: var(--nexus-text-tertiary);
}
</style>
