<template>
  <header class="app-header">
    <!-- 左侧：Logo + 标题 -->
    <div class="header-left">
      <button
        class="sidebar-toggle"
        @click="$emit('toggleSidebar')"
        title="切换侧边栏"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M3 12h18M3 6h18M3 18h18" />
        </svg>
      </button>

      <NexusLogo size="sm" />
      <span class="app-title">Nexus</span>
    </div>

    <!-- 中间：搜索 -->
    <div class="header-center">
      <button class="search-trigger" @click="$emit('openCommandPalette')">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="11" cy="11" r="8" />
          <path d="m21 21-4.35-4.35" />
        </svg>
        <span class="search-placeholder">搜索笔记...</span>
        <kbd class="search-shortcut">⌘K</kbd>
      </button>
    </div>

    <!-- 右侧：操作 -->
    <div class="header-right">
      <button class="header-btn" title="新建笔记 (⌘N)" @click="createNote">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M12 5v14M5 12h14" />
        </svg>
      </button>

      <button class="header-btn" title="设置" @click="openSettings">
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z" />
          <circle cx="12" cy="12" r="3" />
        </svg>
      </button>
    </div>
  </header>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import NexusLogo from '../icons/NexusLogo.vue'

defineProps<{
  sidebarCollapsed: boolean
}>()

defineEmits<{
  toggleSidebar: []
  openCommandPalette: []
}>()

const router = useRouter()

function createNote() {
  // TODO: Phase 3 - 创建新笔记
  console.log('createNote')
}

function openSettings() {
  router.push('/settings')
}
</script>

<style scoped>
.app-header {
  display: flex;
  align-items: center;
  height: var(--nexus-header-height);
  padding: 0 12px;
  background: var(--nexus-surface);
  border-bottom: 1px solid var(--nexus-border);
  flex-shrink: 0;
  user-select: none;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 180px;
}

.sidebar-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  background: transparent;
  color: var(--nexus-text-secondary);
  border-radius: var(--nexus-radius-sm);
  cursor: pointer;
  transition: all 0.15s ease;
}

.sidebar-toggle:hover {
  background: var(--nexus-bg-hover);
  color: var(--nexus-text);
}

.app-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--nexus-text);
  letter-spacing: -0.3px;
}

.header-center {
  flex: 1;
  display: flex;
  justify-content: center;
  max-width: 560px;
  margin: 0 auto;
}

.search-trigger {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  max-width: 400px;
  padding: 6px 12px;
  background: var(--nexus-bg);
  border: 1px solid var(--nexus-border);
  border-radius: var(--nexus-radius-md);
  color: var(--nexus-text-tertiary);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.15s ease;
}

.search-trigger:hover {
  border-color: var(--nexus-border-hover);
  background: var(--nexus-bg-hover);
}

.search-placeholder {
  flex: 1;
  text-align: left;
}

.search-shortcut {
  font-size: 11px;
  padding: 2px 6px;
  background: var(--nexus-surface);
  border: 1px solid var(--nexus-border);
  border-radius: 4px;
  color: var(--nexus-text-tertiary);
  font-family: inherit;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 4px;
  min-width: 180px;
  justify-content: flex-end;
}

.header-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: none;
  background: transparent;
  color: var(--nexus-text-secondary);
  border-radius: var(--nexus-radius-sm);
  cursor: pointer;
  transition: all 0.15s ease;
}

.header-btn:hover {
  background: var(--nexus-bg-hover);
  color: var(--nexus-text);
}
</style>
