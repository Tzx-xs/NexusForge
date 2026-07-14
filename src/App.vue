<template>
  <div id="nexus-app" class="h-screen flex flex-col bg-[#09090b] text-zinc-100 overflow-hidden">
    <AppHeader
      :sidebar-collapsed="sidebarCollapsed"
      @toggle-sidebar="sidebarCollapsed = !sidebarCollapsed"
      @open-command-palette="showCommandPalette = true"
    />

    <div class="flex-1 flex overflow-hidden">
      <AppSidebar
        :collapsed="sidebarCollapsed"
        :active-panel="activePanel"
        @select-panel="activePanel = $event"
        @toggle-collapse="sidebarCollapsed = !sidebarCollapsed"
      />

      <main class="flex-1 overflow-hidden">
        <router-view />
      </main>
    </div>

    <AppStatusBar />

    <!-- Command Palette -->
    <CommandPalette
      v-if="showCommandPalette"
      @close="showCommandPalette = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import AppHeader from './components/layout/AppHeader.vue'
import AppSidebar from './components/layout/AppSidebar.vue'
import AppStatusBar from './components/layout/AppStatusBar.vue'
import CommandPalette from './components/common/CommandPalette.vue'
import { useSettingsStore } from './stores/settings'

const settingsStore = useSettingsStore()
const sidebarCollapsed = ref(settingsStore.settings.layout.sidebarCollapsed)
const activePanel = ref<'folders' | 'tags' | 'search'>('folders')
const showCommandPalette = ref(false)

function handleKeydown(e: KeyboardEvent) {
  if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
    e.preventDefault()
    showCommandPalette.value = !showCommandPalette.value
  }
}

onMounted(() => {
  window.addEventListener('keydown', handleKeydown)
})

onUnmounted(() => {
  window.removeEventListener('keydown', handleKeydown)
})
</script>
