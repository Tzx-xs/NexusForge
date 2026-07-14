import { defineStore } from 'pinia'
import { ref, watch } from 'vue'

export interface ThemeSettings {
  mode: 'dark' | 'light' | 'system'
}

export interface LayoutSettings {
  sidebarWidth: number
  sidebarCollapsed: boolean
}

export interface NotesSettings {
  autoSave: boolean
  autoSaveInterval: number
  showWordCount: boolean
}

export interface SettingsState {
  theme: ThemeSettings
  layout: LayoutSettings
  notes: NotesSettings
}

const STORAGE_KEY = 'nexus-settings'

function loadFromStorage(): Partial<SettingsState> {
  try {
    const saved = localStorage.getItem(STORAGE_KEY)
    return saved ? JSON.parse(saved) : {}
  } catch {
    return {}
  }
}

export const useSettingsStore = defineStore('settings', () => {
  const settings = ref<SettingsState>({
    theme: {
      mode: 'dark',
    },
    layout: {
      sidebarWidth: 256,
      sidebarCollapsed: false,
    },
    notes: {
      autoSave: true,
      autoSaveInterval: 3000,
      showWordCount: true,
    },
    ...loadFromStorage(),
  })

  function updateSettings(partial: Partial<SettingsState>) {
    if (partial.theme) {
      settings.value.theme = { ...settings.value.theme, ...partial.theme }
    }
    if (partial.layout) {
      settings.value.layout = { ...settings.value.layout, ...partial.layout }
    }
    if (partial.notes) {
      settings.value.notes = { ...settings.value.notes, ...partial.notes }
    }
  }

  function resetSettings() {
    settings.value = {
      theme: { mode: 'dark' },
      layout: { sidebarWidth: 256, sidebarCollapsed: false },
      notes: { autoSave: true, autoSaveInterval: 3000, showWordCount: true },
    }
  }

  // 自动持久化
  watch(settings, (newVal) => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(newVal))
    } catch (e) {
      console.error('Failed to save settings:', e)
    }
  }, { deep: true })

  return {
    settings,
    updateSettings,
    resetSettings,
  }
})
