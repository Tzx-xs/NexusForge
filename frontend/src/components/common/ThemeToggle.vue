<template>
  <div class="theme-toggle" :class="{ 'theme-toggle-compact': compact }">
    <button
      v-for="item in themeItems"
      :key="item.mode"
      class="theme-btn"
      :class="{ active: currentMode === item.mode }"
      :title="item.label"
      :aria-label="item.label"
      @click="handleSwitch(item.mode)"
    >
      <component :is="item.icon" class="theme-btn-icon" />
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useThemeStore, type ThemeMode } from '@/stores/theme'
import { Sun, Moon, Stars } from '@vicons/tabler'

defineProps<{
  compact?: boolean
}>()

const themeStore = useThemeStore()

const currentMode = computed(() => themeStore.mode)

const themeItems = [
  { mode: 'light' as ThemeMode, label: '浅色主题', icon: Sun },
  { mode: 'dark' as ThemeMode, label: '深色主题', icon: Moon },
  { mode: 'abyss' as ThemeMode, label: '星渊主题', icon: Stars },
]

function handleSwitch(mode: ThemeMode) {
  themeStore.setMode(mode)
  // 同步到本地存储（即确保 Settings 页面能回读）
  try {
    const saved = localStorage.getItem('xy-settings')
    if (saved) {
      const parsed = JSON.parse(saved)
      if (parsed?.theme) {
        parsed.theme.mode = mode
        localStorage.setItem('xy-settings', JSON.stringify(parsed))
      }
    }
  } catch {
    // ignore
  }
}
</script>

<style scoped>
.theme-toggle {
  display: flex;
  align-items: center;
  gap: 2px;
  padding: 3px;
  border-radius: var(--xy-radius-md);
  border: 1px solid var(--xy-border-1);
  background: var(--xy-surface-3);
}

.theme-toggle-compact {
  gap: 1px;
  padding: 2px;
}

.theme-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  border-radius: var(--xy-radius-sm);
  background: transparent;
  color: var(--xy-text-4);
  cursor: pointer;
  transition: all var(--xy-dur-sm) var(--xy-ease-standard);
  position: relative;
}

.theme-toggle-compact .theme-btn {
  width: 24px;
  height: 24px;
}

.theme-btn:hover {
  color: var(--xy-text-2);
  background: var(--xy-surface-hover);
}

.theme-btn.active {
  color: var(--xy-brand-starlight);
  background: var(--xy-surface-active);
  box-shadow: 0 0 8px rgba(124, 108, 191, 0.15);
}

.theme-btn.active::after {
  content: '';
  position: absolute;
  bottom: 1px;
  left: 50%;
  transform: translateX(-50%);
  width: 6px;
  height: 2px;
  border-radius: 1px;
  background: var(--xy-brand-500);
}

.theme-btn-icon {
  width: 15px;
  height: 15px;
}

.theme-toggle-compact .theme-btn-icon {
  width: 13px;
  height: 13px;
}

@media (prefers-reduced-motion: reduce) {
  .theme-btn {
    transition-duration: 0.01ms !important;
  }
}
</style>
