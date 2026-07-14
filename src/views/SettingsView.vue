<template>
  <div class="settings-view h-full overflow-auto p-8 max-w-2xl mx-auto">
    <h1 class="text-xl font-bold text-zinc-200 mb-6">设置</h1>

    <div class="space-y-6">
      <!-- Appearance -->
      <section class="bg-zinc-900 rounded-xl border border-zinc-800 p-6">
        <h2 class="text-sm font-semibold text-zinc-300 mb-4">外观</h2>
        <div class="space-y-4">
          <div class="flex items-center justify-between">
            <span class="text-sm text-zinc-400">主题模式</span>
            <select
              :value="settingsStore.settings.theme.mode"
              @change="handleThemeChange"
              class="bg-zinc-800 border border-zinc-700 rounded-lg px-3 py-1.5 text-sm text-zinc-300 focus:border-cyan-500 focus:outline-none"
            >
              <option value="system">跟随系统</option>
              <option value="dark">深色</option>
              <option value="light">浅色</option>
            </select>
          </div>
          <div class="flex items-center justify-between">
            <span class="text-sm text-zinc-400">侧边栏宽度</span>
            <span class="text-sm text-zinc-500">{{ settingsStore.settings.layout.sidebarWidth }}px</span>
          </div>
        </div>
      </section>

      <!-- Editor -->
      <section class="bg-zinc-900 rounded-xl border border-zinc-800 p-6">
        <h2 class="text-sm font-semibold text-zinc-300 mb-4">编辑器</h2>
        <div class="space-y-4">
          <div class="flex items-center justify-between">
            <span class="text-sm text-zinc-400">自动保存</span>
            <button
              @click="toggleAutoSave"
              class="relative w-10 h-5 rounded-full transition-colors"
              :class="settingsStore.settings.notes.autoSave ? 'bg-cyan-500' : 'bg-zinc-700'"
            >
              <div
                class="absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white transition-transform"
                :class="{ 'translate-x-5': settingsStore.settings.notes.autoSave }"
              />
            </button>
          </div>
          <div class="flex items-center justify-between">
            <span class="text-sm text-zinc-400">自动保存间隔</span>
            <span class="text-sm text-zinc-500">{{ settingsStore.settings.notes.autoSaveInterval / 1000 }}秒</span>
          </div>
          <div class="flex items-center justify-between">
            <span class="text-sm text-zinc-400">显示字数统计</span>
            <button
              @click="toggleWordCount"
              class="relative w-10 h-5 rounded-full transition-colors"
              :class="settingsStore.settings.notes.showWordCount ? 'bg-cyan-500' : 'bg-zinc-700'"
            >
              <div
                class="absolute top-0.5 left-0.5 w-4 h-4 rounded-full bg-white transition-transform"
                :class="{ 'translate-x-5': settingsStore.settings.notes.showWordCount }"
              />
            </button>
          </div>
        </div>
      </section>

      <!-- About -->
      <section class="bg-zinc-900 rounded-xl border border-zinc-800 p-6">
        <h2 class="text-sm font-semibold text-zinc-300 mb-4">关于</h2>
        <div class="space-y-2 text-sm text-zinc-500">
          <p>Nexus 本地知识库 v0.1.0</p>
          <p>基于 Vue 3 + TypeScript + Tailwind CSS</p>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useSettingsStore } from '@/stores/settings'

const settingsStore = useSettingsStore()

const handleThemeChange = (e: Event) => {
  const target = e.target as HTMLSelectElement
  settingsStore.updateSettings({
    theme: {
      ...settingsStore.settings.theme,
      mode: target.value as 'dark' | 'light' | 'system'
    }
  })
}

const toggleAutoSave = () => {
  settingsStore.updateSettings({
    notes: {
      ...settingsStore.settings.notes,
      autoSave: !settingsStore.settings.notes.autoSave
    }
  })
}

const toggleWordCount = () => {
  settingsStore.updateSettings({
    notes: {
      ...settingsStore.settings.notes,
      showWordCount: !settingsStore.settings.notes.showWordCount
    }
  })
}
</script>
