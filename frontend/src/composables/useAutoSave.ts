import { onUnmounted, ref } from 'vue'
import { useSaveStatusStore } from '@/stores/saveStatus'

export function useAutoSave(
  editorRef: { value: HTMLDivElement | null },
  getCurrentChapter: () => { id: string } | null | undefined,
  updateChapter: (id: string, data: { content: string }) => void,
  delay = 2000,
  getContent?: () => string
) {
  let saveTimer: ReturnType<typeof setTimeout> | null = null
  const lastSavedTime = ref<Date | null>(null)
  const isSaving = ref(false)
  const saveStatusStore = useSaveStatusStore()

  function saveContent() {
    if (!editorRef.value || !getCurrentChapter()) return

    if (saveTimer) clearTimeout(saveTimer)
    saveTimer = setTimeout(() => {
      const chapter = getCurrentChapter()
      if (chapter && editorRef.value) {
        isSaving.value = true
        saveStatusStore.setIsSaving(true)
        try {
          const content = getContent ? getContent() : editorRef.value!.innerHTML
          updateChapter(chapter.id, {
            content,
          })
          lastSavedTime.value = new Date()
          saveStatusStore.setLastSavedTime(lastSavedTime.value)
        } finally {
          isSaving.value = false
          saveStatusStore.setIsSaving(false)
        }
      }
    }, delay)
  }

  function cancelPendingSave() {
    if (saveTimer) {
      clearTimeout(saveTimer)
      saveTimer = null
    }
  }

  onUnmounted(() => {
    cancelPendingSave()
  })

  return {
    saveContent,
    cancelPendingSave,
    lastSavedTime,
    isSaving,
  }
}
