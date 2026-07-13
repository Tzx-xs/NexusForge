<template>
  <WorkspaceShell>
    <template #chapterRail>
      <WritingSidebar />
    </template>

    <template #default>
      <div class="workspace-content">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </div>
    </template>

    <template #contextPanel>
      <ContextPanel />
    </template>
  </WorkspaceShell>
</template>

<script setup lang="ts">
import { WorkspaceShell, ContextPanel, WritingSidebar } from '@/components/workspace'
</script>

<style scoped>
.workspace-content {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--xy-bg-canvas);
  overflow: hidden;
}

.workspace-content :deep(.fade-enter-active),
.workspace-content :deep(.fade-leave-active) {
  transition: opacity 0.2s ease;
}

.workspace-content :deep(.fade-enter-from),
.workspace-content :deep(.fade-leave-to) {
  opacity: 0;
}
</style>
