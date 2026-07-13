<template>
  <div ref="wrapperRef" class="theme-switcher">
    <!-- 切换按钮 -->
    <button
      class="ts-btn"
      :aria-label="`当前主题：${currentLabel}，点击切换`"
      @click="toggleMenu"
    >
      <component :is="currentIcon" class="ts-btn-icon" />
    </button>

    <!-- 下拉菜单 -->
    <Transition name="ts-menu">
      <div v-if="menuOpen" class="ts-menu">
        <div
          v-for="opt in themeOptions"
          :key="opt.value"
          class="ts-option"
          :class="{ 'ts-option-active': themeStore.mode === opt.value }"
          @click="selectTheme(opt.value)"
        >
          <div class="ts-option-preview" :style="opt.previewStyle" />
          <span class="ts-option-label">{{ opt.label }}</span>
          <Check v-if="themeStore.mode === opt.value" class="ts-option-check" />
        </div>
        <div class="ts-divider" />
        <div class="ts-option ts-option-system" @click="selectTheme('system')">
          <DeviceDesktop class="ts-option-preview ts-system-icon" />
          <span class="ts-option-label">跟随系统</span>
          <Check v-if="themeStore.mode === 'system'" class="ts-option-check" />
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, type Component } from 'vue'
import { useThemeStore, type ThemeMode } from '@/stores/theme'
import {
  Sun,
  Moon,
  Check,
  DeviceDesktop,
} from '@vicons/tabler'

const themeStore = useThemeStore()

const menuOpen = ref(false)
const wrapperRef = ref<HTMLElement | null>(null)

const themeOptions: Array<{
  value: Exclude<ThemeMode, 'system'>
  label: string
  icon: Component
  previewStyle: Record<string, string>
}> = [
  {
    value: 'abyss',
    label: '暗渊紫',
    icon: Moon,
    previewStyle: {
      background: '#141127',
      border: '1px solid rgba(124,108,191,0.18)',
    },
  },
  {
    value: 'light',
    label: '明亮浅色',
    icon: Sun,
    previewStyle: {
      background: '#ffffff',
      border: '1px solid rgba(15,23,42,0.1)',
    },
  },
]

const currentIcon = computed(() => {
  if (themeStore.mode === 'system') {
    return themeStore.effectiveMode === 'light' ? Sun : Moon
  }
  return themeStore.mode === 'light' ? Sun : Moon
})

const currentLabel = computed(() => {
  const map: Record<string, string> = {
    abyss: '暗渊紫',
    light: '明亮浅色',
    system: '跟随系统',
  }
  return map[themeStore.mode] ?? themeStore.mode
})

function toggleMenu() {
  menuOpen.value = !menuOpen.value
}

defineExpose({ toggleMenu })

function selectTheme(mode: ThemeMode) {
  themeStore.setMode(mode)
  // 同步到 xy-settings localStorage（确保 Settings 页面能回读当前主题）
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
  menuOpen.value = false
}

// 点击外部关闭
function handleClickOutside(e: MouseEvent) {
  if (wrapperRef.value && !wrapperRef.value.contains(e.target as Node)) {
    menuOpen.value = false
  }
}

onMounted(() => document.addEventListener('click', handleClickOutside))
onUnmounted(() => document.removeEventListener('click', handleClickOutside))
</script>

<style scoped>
.theme-switcher {
  position: relative;
  display: inline-flex;
}

/* === 切换按钮 === */
.ts-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border: none;
  border-radius: var(--xy-radius-md);
  background: transparent;
  color: var(--xy-text-3);
  cursor: pointer;
  transition: all var(--xy-dur-sm) var(--xy-ease-standard);
}

.ts-btn:hover {
  background: var(--xy-surface-hover);
  color: var(--xy-brand-starlight);
}

.ts-btn:active {
  background: var(--xy-surface-active);
  transform: scale(0.92);
}

.ts-btn-icon {
  width: 16px;
  height: 16px;
  transition: transform var(--xy-dur-md) var(--xy-ease-spring);
}

.ts-btn:hover .ts-btn-icon {
  transform: rotate(15deg);
}

/* === 下拉菜单 === */
.ts-menu {
  position: absolute;
  top: calc(100% + 6px);
  right: 0;
  min-width: 180px;
  background: var(--xy-surface-1);
  border: 1px solid var(--xy-border-1);
  border-radius: var(--xy-radius-lg);
  box-shadow: var(--xy-shadow-lg);
  padding: 6px;
  z-index: var(--xy-z-dropdown);
  backdrop-filter: blur(16px);
  -webkit-backdrop-filter: blur(16px);
}

.ts-menu-enter-active {
  animation: ts-menu-in var(--xy-dur-md) var(--xy-ease-enter) both;
}
.ts-menu-leave-active {
  animation: ts-menu-out var(--xy-dur-sm) var(--xy-ease-exit) both;
}

@keyframes ts-menu-in {
  from {
    opacity: 0;
    transform: translateY(-6px) scale(0.96);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}
@keyframes ts-menu-out {
  from {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
  to {
    opacity: 0;
    transform: translateY(-6px) scale(0.96);
  }
}

/* === 选项 === */
.ts-option {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border-radius: var(--xy-radius-md);
  cursor: pointer;
  transition: background var(--xy-dur-xs) var(--xy-ease-standard);
  font-size: 13px;
  color: var(--xy-text-2);
}

.ts-option:hover {
  background: var(--xy-surface-hover);
  color: var(--xy-text-1);
}

.ts-option-active {
  color: var(--xy-brand-starlight);
  font-weight: 600;
}

.ts-option-preview {
  width: 22px;
  height: 22px;
  border-radius: var(--xy-radius-sm);
  flex-shrink: 0;
}

.ts-system-icon {
  width: 22px;
  height: 22px;
  padding: 3px;
  color: var(--xy-text-3);
}

.ts-option-label {
  flex: 1;
}

.ts-option-check {
  width: 14px;
  height: 14px;
  color: var(--xy-brand-500);
}

.ts-divider {
  height: 1px;
  background: var(--xy-border-1);
  margin: 4px 6px;
}

.ts-option-system {
  font-size: 12px;
}
</style>
