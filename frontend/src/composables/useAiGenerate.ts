import { ref } from 'vue'
import type { Editor } from '@tiptap/vue-3'
import { useChapterStore } from '@/stores/chapter'
import { getGenerateContentUrl, getAuthHeaders } from '@/api/chapters'
import { parseSseBlocks, type SseEvent } from '@/utils/sseParser'
import { createTimeoutSignal, combineAbortSignals } from '@/utils/abortSignalPolyfill'

export function useAiGenerate(
  editorRef: { value: HTMLDivElement | null },
  onContentChange?: () => void,
  editor?: { value: Editor | null }
) {
  const isAiGenerating = ref(false)
  const generatedContent = ref('')
  const error = ref<string | null>(null)
  const progress = ref(0)

  let abortController: AbortController | null = null
  let aiParagraphEl: HTMLElement | null = null

  function resetRunState() {
    generatedContent.value = ''
    error.value = null
    progress.value = 0
    aiParagraphEl = null
  }

  function appendDeltaToEditor(delta: string) {
    if (!delta) return
    if (editor?.value) {
      // Tiptap 模式：在文档末尾追加文本
      const endPos = editor.value.state.doc.content.size
      editor.value.commands.insertContentAt(endPos, delta)
      return
    }
    // 回退模式：DOM 直接追加
    if (!editorRef.value) return
    if (!aiParagraphEl) {
      aiParagraphEl = document.createElement('p')
      aiParagraphEl.className = 'paragraph'
      aiParagraphEl.setAttribute('data-ai-generated', 'true')
      editorRef.value.appendChild(aiParagraphEl)
    }
    aiParagraphEl.appendChild(document.createTextNode(delta))
  }

  function handleSseEvent(evt: SseEvent): 'complete' | 'error' | null {
    let payload: Record<string, unknown> = {}
    if (evt.data) {
      try {
        payload = JSON.parse(evt.data)
      } catch {
        payload = {}
      }
    }

    switch (evt.event) {
      case 'token': {
        const delta = (payload.delta as string) || ''
        if (delta) {
          generatedContent.value += delta
          appendDeltaToEditor(delta)
        }
        break
      }
      case 'progress': {
        const percent = Number(payload.percent)
        if (!Number.isNaN(percent)) {
          progress.value = percent
        }
        break
      }
      case 'complete':
        return 'complete'
      case 'error': {
        const message = (payload.message as string) || '生成失败'
        error.value = message
        return 'error'
      }
    }
    return null
  }

  async function handleAiContinue() {
    if (isAiGenerating.value) return

    const chapterStore = useChapterStore()
    const chapterId = chapterStore.currentChapter?.id
    if (!chapterId) {
      error.value = '未找到当前章节，无法生成'
      return
    }

    isAiGenerating.value = true
    resetRunState()
    abortController = new AbortController()

    // M-02: 统一 120 秒 SSE 超时，与用户取消的 AbortController 合并
    const { signal: timeoutSignal, cleanup: timeoutCleanup } = createTimeoutSignal(120_000)
    const { signal: combinedSignal, cleanup: combineCleanup } = combineAbortSignals([abortController.signal, timeoutSignal])

    try {
      const response = await fetch(getGenerateContentUrl(chapterId), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'text/event-stream',
          ...getAuthHeaders(),
        },
        signal: combinedSignal,
      })

      if (!response.ok) {
        let msg = `生成请求失败 (${response.status})`
        try {
          const errBody = await response.json()
          if (errBody?.detail) msg = errBody.detail
          else if (errBody?.message) msg = errBody.message
        } catch {
          // 忽略 JSON 解析失败，使用默认消息
        }
        error.value = msg
        return
      }

      if (!response.body) {
        error.value = '响应体为空'
        return
      }

      const reader = response.body.getReader()
      const decoder = new TextDecoder('utf-8')
      let buffer = ''
      let terminal: 'complete' | 'error' | null = null

      while (terminal === null) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, '\n')

        const lastSep = buffer.lastIndexOf('\n\n')
        if (lastSep === -1) continue

        const ready = buffer.slice(0, lastSep + 2)
        buffer = buffer.slice(lastSep + 2)

        for (const evt of parseSseBlocks(ready)) {
          terminal = handleSseEvent(evt)
          if (terminal !== null) break
        }
      }

      // flush decoder 并处理尾部残留
      const tail = decoder.decode()
      if (tail) buffer += tail
      if (terminal === null && buffer.trim()) {
        for (const evt of parseSseBlocks(buffer)) {
          terminal = handleSseEvent(evt)
          if (terminal !== null) break
        }
      }
    } catch (err: unknown) {
      if (err instanceof DOMException && err.name === 'AbortError') {
        // 用户主动取消，不计入错误
      } else if (err instanceof TypeError && err.message?.includes('fetch')) {
        error.value = '网络连接失败，请检查网络后重试'
      } else if (err instanceof DOMException && err.name === 'TimeoutError') {
        error.value = '请求超时，请稍后重试'
      } else if (err instanceof Error) {
        error.value = err.message || '生成失败'
      } else {
        error.value = '网络错误，生成失败'
      }
    } finally {
      isAiGenerating.value = false
      abortController = null
      onContentChange?.()
      // 清理超时定时器与合并信号监听器，避免内存泄漏
      combineCleanup()
      timeoutCleanup()
    }
  }

  function abort() {
    if (abortController) {
      abortController.abort()
    }
  }

  return {
    isAiGenerating,
    generatedContent,
    error,
    progress,
    handleAiContinue,
    abort,
  }
}
