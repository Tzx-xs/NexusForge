import { ref } from 'vue'
import type { Editor } from '@tiptap/vue-3'

const WORD_COUNT_DEBOUNCE_MS = 250

export function useWordCount(
  editorRef: { value: HTMLDivElement | null },
  editor?: { value: Editor | null }
) {
  const wordCount = ref(0)
  let timer: ReturnType<typeof setTimeout> | null = null

  function countWords(text: string): number {
    const chineseChars = (text.match(/[\u4e00-\u9fa5]/g) || []).length
    const englishWords = (text.match(/[a-zA-Z]+/g) || []).length
    return chineseChars + englishWords
  }

  function updateWordCount() {
    if (timer !== null) {
      clearTimeout(timer)
      timer = null
    }
    if (editor?.value) {
      wordCount.value = countWords(editor.value.getText())
      return
    }
    if (editorRef.value) {
      const text = editorRef.value.textContent || ''
      wordCount.value = countWords(text)
    }
  }

  /**
   * B14 性能优化：长文场景下每次按键都全量遍历文档统计字数开销大，
   * 改为防抖（250ms）触发，避免大文档卡顿。章节切换 / 挂载时仍用 updateWordCount 立即刷新。
   */
  function updateWordCountDebounced() {
    if (timer !== null) clearTimeout(timer)
    timer = setTimeout(updateWordCount, WORD_COUNT_DEBOUNCE_MS)
  }

  return {
    wordCount,
    countWords,
    updateWordCount,
    updateWordCountDebounced,
  }
}
