import { defineStore } from 'pinia'
import { ref } from 'vue'

/**
 * 自动保存状态共享 store
 *
 * 用途：让 useAutoSave（在 EditorPanel 内调用）写入 lastSavedTime/isSaving，
 * 供 WorkspaceShell 状态栏读取，避免通过多层 props/slot 透传。
 */
export const useSaveStatusStore = defineStore('saveStatus', () => {
  const lastSavedTime = ref<Date | null>(null)
  const isSaving = ref(false)

  function setLastSavedTime(time: Date | null) {
    lastSavedTime.value = time
  }

  function setIsSaving(saving: boolean) {
    isSaving.value = saving
  }

  return {
    lastSavedTime,
    isSaving,
    setLastSavedTime,
    setIsSaving,
  }
})
