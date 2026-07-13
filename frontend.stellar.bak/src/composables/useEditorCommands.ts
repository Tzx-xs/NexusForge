/**
 * NOTE: document.execCommand 已废弃（MDN 标记 deprecated），但在简单富文本编辑器
 * 场景下仍可工作。当前实现优先使用 Tiptap editor（若提供），回退到 execCommand
 * 以保持向后兼容。后续如需移除 execCommand，可删除回退分支。
 */
import { ref } from 'vue'
import type { Editor } from '@tiptap/vue-3'

export function useEditorCommands(
  editorRef: { value: HTMLDivElement | null },
  onChange?: () => void,
  editor?: { value: Editor | null }
) {
  const canUndo = ref(false)
  const canRedo = ref(false)

  function updateUndoRedoState() {
    if (editor?.value) {
      canUndo.value = editor.value.can().undo()
      canRedo.value = editor.value.can().redo()
      return
    }
    try {
      canUndo.value = document.queryCommandEnabled('undo')
      canRedo.value = document.queryCommandEnabled('redo')
    } catch (e) {
      // ignore
    }
  }

  function execCommand(command: string, value?: string) {
    if (editor?.value) {
      const chain = editor.value.chain().focus()
      switch (command) {
        case 'undo':
          chain.undo().run()
          break
        case 'redo':
          chain.redo().run()
          break
        case 'bold':
          chain.toggleBold().run()
          break
        case 'italic':
          chain.toggleItalic().run()
          break
        case 'underline':
          chain.toggleUnderline().run()
          break
        case 'strikeThrough':
          chain.toggleStrike().run()
          break
        case 'formatBlock':
          if (value === 'h1') chain.toggleHeading({ level: 1 }).run()
          else if (value === 'h2') chain.toggleHeading({ level: 2 }).run()
          else if (value === 'h3') chain.toggleHeading({ level: 3 }).run()
          else if (value === 'blockquote') chain.toggleBlockquote().run()
          else if (value === 'pre') chain.toggleCodeBlock().run()
          break
        case 'justifyLeft':
          chain.setTextAlign('left').run()
          break
        case 'justifyCenter':
          chain.setTextAlign('center').run()
          break
        case 'justifyRight':
          chain.setTextAlign('right').run()
          break
      }
      updateUndoRedoState()
      onChange?.()
      return
    }
    // 回退到 execCommand（向后兼容）
    if (!editorRef.value) return
    editorRef.value.focus()
    try {
      document.execCommand(command, false, value)
      updateUndoRedoState()
      onChange?.()
    } catch (e) {
      console.error('execCommand failed:', command, e)
    }
  }

  return {
    canUndo,
    canRedo,
    execCommand,
    updateUndoRedoState,
  }
}
