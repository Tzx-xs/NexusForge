import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  getSettings as apiGetSettings,
  updateSettings as apiUpdateSettings,
  resetSettings as apiResetSettings,
  type SettingsData,
} from '@/api/settings'

function validateSettings(raw: unknown): SettingsData {
  if (typeof raw !== 'object' || raw === null || Array.isArray(raw)) {
    return {}
  }
  const result: SettingsData = {}
  for (const [key, value] of Object.entries(raw as Record<string, unknown>)) {
    if (typeof value === 'string') {
      result[key] = value
    }
  }
  return result
}

function loadFromLocalStorage(): SettingsData {
  try {
    const saved = localStorage.getItem('xy-settings')
    if (saved) {
      return validateSettings(JSON.parse(saved))
    }
  } catch (e) {
    console.error('Failed to parse settings from localStorage:', e)
  }
  return {}
}

export const useSettingsStore = defineStore('settings', () => {
  const settings = ref<SettingsData>(loadFromLocalStorage())
  const loading = ref(false)

  async function fetchSettings() {
    loading.value = true
    try {
      const data = await apiGetSettings()
      settings.value = data
      localStorage.setItem('xy-settings', JSON.stringify(settings.value))
    } catch (e) {
      console.error('Failed to fetch settings, using localStorage fallback:', e)
      settings.value = loadFromLocalStorage()
    } finally {
      loading.value = false
    }
  }

  async function saveSettings(data: Partial<SettingsData>) {
    try {
      const result = await apiUpdateSettings(data)
      settings.value = result
      localStorage.setItem('xy-settings', JSON.stringify(settings.value))
      return result
    } catch (e) {
      console.error('Failed to save settings to backend, saving locally:', e)
      Object.assign(settings.value, data)
      localStorage.setItem('xy-settings', JSON.stringify(settings.value))
      return settings.value
    }
  }

  async function resetSettings() {
    try {
      const result = await apiResetSettings()
      settings.value = result
      localStorage.setItem('xy-settings', JSON.stringify(settings.value))
      return result
    } catch (e) {
      console.error('Failed to reset settings:', e)
      return null
    }
  }

  return {
    settings,
    loading,
    fetchSettings,
    saveSettings,
    resetSettings,
  }
})
