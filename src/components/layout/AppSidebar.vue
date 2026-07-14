<template>
  <aside class="app-sidebar" :class="{ collapsed }">
    <!-- 面板切换标签 -->
    <div class="sidebar-tabs">
      <button
        class="tab-btn"
        :class="{ active: activePanel === 'folders' }"
        @click="$emit('selectPanel', 'folders')"
        title="文件夹"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M4 20h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-7.93a2 2 0 0 1-1.66-.9l-.82-1.2A2 2 0 0 0 7.93 3H4a2 2 0 0 0-2 2v13c0 1.1.9 2 2 2Z" />
        </svg>
        <span v-if="!collapsed" class="tab-label">文件夹</span>
      </button>

      <button
        class="tab-btn"
        :class="{ active: activePanel === 'tags' }"
        @click="$emit('selectPanel', 'tags')"
        title="标签"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M12 2H2v10l9.29 9.29c.94.94 2.48.94 3.42 0l6.58-6.58c.94-.94.94-2.48 0-3.42L12 2Z" />
          <path d="M7 7h.01" />
        </svg>
        <span v-if="!collapsed" class="tab-label">标签</span>
      </button>

      <button
        class="tab-btn"
        :class="{ active: activePanel === 'search' }"
        @click="$emit('selectPanel', 'search')"
        title="搜索"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="11" cy="11" r="8" />
          <path d="m21 21-4.35-4.35" />
        </svg>
        <span v-if="!collapsed" class="tab-label">搜索</span>
      </button>
    </div>

    <!-- 面板内容 -->
    <div class="sidebar-content" v-if="!collapsed">
      <FolderPanel v-if="activePanel === 'folders'" />
      <TagPanel v-else-if="activePanel === 'tags'" />
      <SearchPanel v-else-if="activePanel === 'search'" />
    </div>

    <!-- 折叠按钮 -->
    <button class="collapse-btn" @click="$emit('toggleCollapse')" :title="collapsed ? '展开侧边栏' : '折叠侧边栏'">
      <svg
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        :style="{ transform: collapsed ? 'rotate(180deg)' : '' }"
      >
        <path d="m15 18-6-6 6-6" />
      </svg>
    </button>
  </aside>
</template>

<script setup lang="ts">
import FolderPanel from '../sidebar/FolderPanel.vue'
import TagPanel from '../sidebar/TagPanel.vue'
import SearchPanel from '../sidebar/SearchPanel.vue'

defineProps<{
  collapsed: boolean
  activePanel: 'folders' | 'tags' | 'search'
}>()

defineEmits<{
  selectPanel: [panel: 'folders' | 'tags' | 'search']
  toggleCollapse: []
}>()
</script>

<style scoped>
.app-sidebar {
  display: flex;
  flex-direction: column;
  width: var(--nexus-sidebar-width);
  background: var(--nexus-surface);
  border-right: 1px solid var(--nexus-border);
  transition: width 0.2s ease;
  flex-shrink: 0;
  position: relative;
}

.app-sidebar.collapsed {
  width: var(--nexus-sidebar-width-collapsed);
}

.sidebar-tabs {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding: 8px;
  border-bottom: 1px solid var(--nexus-border);
}

.tab-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px;
  border: none;
  background: transparent;
  color: var(--nexus-text-secondary);
  border-radius: var(--nexus-radius-sm);
  cursor: pointer;
  transition: all 0.15s ease;
  font-size: 13px;
  text-align: left;
  white-space: nowrap;
}

.tab-btn:hover {
  background: var(--nexus-bg-hover);
  color: var(--nexus-text);
}

.tab-btn.active {
  background: var(--nexus-bg-active);
  color: var(--nexus-text);
}

.tab-label {
  flex: 1;
}

.sidebar-content {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.collapse-btn {
  position: absolute;
  right: -12px;
  top: 50%;
  transform: translateY(-50%);
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--nexus-surface);
  border: 1px solid var(--nexus-border);
  color: var(--nexus-text-secondary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.15s ease;
  z-index: 10;
}

.app-sidebar:hover .collapse-btn {
  opacity: 1;
}

.collapse-btn:hover {
  background: var(--nexus-bg-hover);
  color: var(--nexus-text);
}
</style>
