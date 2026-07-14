<template>
  <div class="search-panel">
    <div class="search-input-wrap">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="11" cy="11" r="8" />
        <path d="m21 21-4.35-4.35" />
      </svg>
      <input
        v-model="searchQuery"
        class="search-input"
        type="text"
        placeholder="搜索笔记内容..."
      />
    </div>
    <div class="search-results">
      <p class="empty-hint">输入关键词开始搜索</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const searchQuery = ref('')
</script>

<style scoped>
.search-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}
.search-input-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 8px 12px;
  padding: 6px 10px;
  background: var(--nexus-bg);
  border: 1px solid var(--nexus-border);
  border-radius: var(--nexus-radius-md);
  color: var(--nexus-text-secondary);
}
.search-input {
  flex: 1;
  background: none;
  border: none;
  outline: none;
  color: var(--nexus-text);
  font-size: 13px;
  font-family: inherit;
}
.search-input::placeholder {
  color: var(--nexus-text-tertiary);
}
.search-results {
  flex: 1;
  overflow-y: auto;
  padding: 0 12px;
}
.empty-hint {
  font-size: 13px;
  color: var(--nexus-text-tertiary);
  text-align: center;
  padding: 24px 0;
}
</style>
