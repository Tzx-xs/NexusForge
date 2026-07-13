import { defineStore } from 'pinia'
import { ref, computed, watch, markRaw } from 'vue'
import { darkTheme, lightTheme, type GlobalTheme } from 'naive-ui'

export type ThemeMode = 'light' | 'dark' | 'abyss' | 'system'

export const useThemeStore = defineStore('theme', () => {
  // 从 localStorage 读取初始值（默认 'abyss'，与 :root 中 Abyss 色值匹配）
  function getInitialMode(): ThemeMode {
    // B7 修复：优先从独立 key `xy-theme` 读取，避免与 settings store 共写 `xy-settings` 互相覆盖
    try {
      const t = localStorage.getItem('xy-theme')
      if (t) {
        const m = JSON.parse(t)?.mode
        if (['light', 'dark', 'abyss', 'system'].includes(m)) return m
      }
    } catch {
      // ignore
    }
    try {
      const saved = localStorage.getItem('xy-settings')
      if (saved) {
        const parsed = JSON.parse(saved)
        const mode = parsed?.theme?.mode
        if (['light', 'dark', 'abyss', 'system'].includes(mode)) return mode
      }
    } catch {
      // ignore
    }
    return 'abyss'
  }

  const mode = ref<ThemeMode>(getInitialMode())

  // 解析 system → 实际主题（light/dark）
  function resolveSystem(): 'light' | 'dark' {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
  }

  // 实际生效主题（system 已解析；abyss 保留品牌特色）
  const effectiveMode = computed<'light' | 'dark' | 'abyss'>(() => {
    if (mode.value === 'system') {
      return resolveSystem() === 'dark' ? 'dark' : 'light'
    }
    return mode.value
  })

  // naive-ui GlobalTheme（abyss 归入 darkTheme，保持深色调）
  const appTheme = computed<GlobalTheme>(() => {
    return markRaw(effectiveMode.value === 'light' ? lightTheme : darkTheme)
  })

  // 同步 data-theme 到 <html>，触发 CSS 变量切换
  function applyDataTheme() {
    document.documentElement.setAttribute('data-theme', effectiveMode.value)
  }

  // 设置模式（由 Settings.vue / ThemeSwitcher / Ctrl+Shift+L 调用）
  function setMode(newMode: ThemeMode) {
    mode.value = newMode
    // B7 修复：独立持久化主题到 `xy-theme`，与 settings store 解耦，避免互相覆盖导致主题丢失
    try {
      localStorage.setItem('xy-theme', JSON.stringify({ mode: newMode }))
    } catch {
      // ignore
    }
    // 兼容旧逻辑：同步到 xy-settings（确保旧版 Settings 回读仍可用）
    try {
      const saved = localStorage.getItem('xy-settings')
      if (saved) {
        const parsed = JSON.parse(saved)
        if (parsed?.theme) {
          parsed.theme.mode = newMode
          localStorage.setItem('xy-settings', JSON.stringify(parsed))
        }
      }
    } catch {
      // ignore
    }
  }

  // Sprint 6.1: Ctrl+Shift+L 快捷键循环切换主题
  // system 状态下,先解析为实际主题(light/dark),再由下次 toggle 进入循环
  function toggleMode() {
    if (mode.value === 'system') {
      setMode(effectiveMode.value)
      return
    }
    const order: ThemeMode[] = ['light', 'dark', 'abyss']
    const idx = order.indexOf(mode.value)
    setMode(order[(idx + 1) % order.length])
  }

  // 初始化（在 App.vue setup 调用一次）
  let mediaListener: ((e: MediaQueryListEvent) => void) | null = null

  function init() {
    applyDataTheme()
    // 监听 system 主题变化（仅当 mode === 'system' 时响应）
    mediaListener = () => {
      if (mode.value === 'system') applyDataTheme()
    }
    window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', mediaListener)
  }

  function destroy() {
    if (mediaListener) {
      window.matchMedia('(prefers-color-scheme: dark)').removeEventListener('change', mediaListener)
      mediaListener = null
    }
  }

  // 监听 mode 变化，自动应用 data-theme
  watch(mode, () => {
    applyDataTheme()
  })

  return {
    mode,
    effectiveMode,
    appTheme,
    setMode,
    toggleMode,
    init,
    destroy,
  }
})
