import { defineStore } from 'pinia'
import { ref } from 'vue'

/**
 * 编辑器光标状态 store
 *
 * 用途：EditorPanel 写入光标位置（cursorLine/cursorCol），
 * 供 WorkspaceShell 状态栏读取，避免通过多层 props 透传。
 */
export const useEditorStatusStore = defineStore('editorStatus', () => {
  const cursorLine = ref(1)
  const cursorCol = ref(1)

  function setCursor(line: number, col: number) {
    cursorLine.value = line
    cursorCol.value = col
  }

  return { cursorLine, cursorCol, setCursor }
})
