import { defineStore } from 'pinia'
import { ref } from 'vue'
import {
  getCharacterList,
  createCharacter as apiCreateCharacter,
  updateCharacter as apiUpdateCharacter,
  deleteCharacter as apiDeleteCharacter,
  getSettingList,
  createSetting as apiCreateSetting,
  updateSetting as apiUpdateSetting,
  deleteSetting as apiDeleteSetting,
  type Character,
  type WorldSetting,
} from '@/api/bible'

export const useBibleStore = defineStore('bible', () => {
  const characters = ref<Character[]>([])
  const settings = ref<WorldSetting[]>([])
  const loading = ref(false)

  async function fetchCharacters(novelId: string) {
    loading.value = true
    try {
      const data = await getCharacterList(novelId)
      characters.value = data
    } catch (e) {
      console.error('Failed to fetch characters:', e)
      characters.value = []
    } finally {
      loading.value = false
    }
  }

  async function createCharacter(novelId: string, data: Parameters<typeof apiCreateCharacter>[1]) {
    const result = await apiCreateCharacter(novelId, data)
    characters.value.push(result)
    return result
  }

  async function updateCharacter(characterId: string, data: Partial<Character>) {
    const result = await apiUpdateCharacter(characterId, data)
    const index = characters.value.findIndex((c) => c.id === characterId)
    if (index !== -1) {
      characters.value[index] = result
    }
    return result
  }

  async function deleteCharacter(characterId: string) {
    await apiDeleteCharacter(characterId)
    characters.value = characters.value.filter((c) => c.id !== characterId)
  }

  async function fetchSettings(novelId: string, settingType?: string) {
    try {
      const data = await getSettingList(novelId, settingType)
      settings.value = data
    } catch (e) {
      console.error('Failed to fetch settings:', e)
      settings.value = []
    }
  }

  async function createSetting(novelId: string, data: Parameters<typeof apiCreateSetting>[1]) {
    const result = await apiCreateSetting(novelId, data)
    settings.value.push(result)
    return result
  }

  async function updateSetting(settingId: string, data: Partial<WorldSetting>) {
    const result = await apiUpdateSetting(settingId, data)
    const index = settings.value.findIndex((s) => s.id === settingId)
    if (index !== -1) {
      settings.value[index] = result
    }
    return result
  }

  async function deleteSetting(settingId: string) {
    await apiDeleteSetting(settingId)
    settings.value = settings.value.filter((s) => s.id !== settingId)
  }

  return {
    characters,
    settings,
    loading,
    fetchCharacters,
    createCharacter,
    updateCharacter,
    deleteCharacter,
    fetchSettings,
    createSetting,
    updateSetting,
    deleteSetting,
  }
})
