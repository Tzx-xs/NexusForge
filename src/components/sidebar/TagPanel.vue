<template>
  <div class="tag-panel">
    <div class="panel-header">
      <span class="panel-title">标签</span>
    </div>
    <div class="tag-list">
      <p class="empty-hint">暂无标签</p>
    </div>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
.tag-panel {
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
.tag-list {
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
