import { ref, computed } from 'vue'

export interface EditorState {
  content: string
  filePath: string | null
  isDirty: boolean
  undoStack: string[]
  redoStack: string[]
}

const state = ref<EditorState>({
  content: '',
  filePath: null,
  isDirty: false,
  undoStack: [],
  redoStack: [],
})

const maxUndoSize = 100

export function useEditor() {
  const setContent = (content: string, filePath?: string, markDirty = true) => {
    if (state.value.content !== content) {
      // Push to undo stack
      state.value.undoStack.push(state.value.content)
      if (state.value.undoStack.length > maxUndoSize) {
        state.value.undoStack.shift()
      }
      state.value.redoStack = []
    }

    state.value.content = content
    state.value.isDirty = markDirty
    if (filePath !== undefined) {
      state.value.filePath = filePath
    }
  }

  const undo = () => {
    if (state.value.undoStack.length === 0) return

    state.value.redoStack.push(state.value.content)
    state.value.content = state.value.undoStack.pop()!
  }

  const redo = () => {
    if (state.value.redoStack.length === 0) return

    state.value.undoStack.push(state.value.content)
    state.value.content = state.value.redoStack.pop()!
  }

  const markSaved = () => {
    state.value.isDirty = false
  }

  const clear = () => {
    state.value.content = ''
    state.value.filePath = null
    state.value.isDirty = false
    state.value.undoStack = []
    state.value.redoStack = []
  }

  const canUndo = computed(() => state.value.undoStack.length > 0)
  const canRedo = computed(() => state.value.redoStack.length > 0)

  return {
    state,
    setContent,
    undo,
    redo,
    markSaved,
    clear,
    canUndo,
    canRedo,
  }
}
