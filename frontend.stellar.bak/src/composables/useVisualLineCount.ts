import { ref, watch, onMounted, onUnmounted, type Ref } from 'vue'
import type { Editor } from '@tiptap/vue-3'

const DEFAULT_LINE_HEIGHT = 31.2
const MIN_LINES = 99
const DEBOUNCE_MS = 100

/**
 * 计算编辑器视觉行号信息。
 *
 * - 使用 ProseMirror view.coordsAtPos 采样每个文本位置的 top 坐标，识别真实换行。
 * - 始终返回至少 MIN_LINES（99）行，不足时按默认行高线性补齐。
 * - 超过 99 行后按实际渲染行数继续递增。
 */
export function useVisualLineCount(
  editor: Ref<Editor | undefined>,
  scrollContainerRef: Ref<HTMLElement | null>,
) {
  const visualLineCount = ref(MIN_LINES)
  const lineOffsets = ref<number[]>([])

  let rafId: number | null = null
  let resizeObserver: ResizeObserver | null = null
  let debounceTimer: ReturnType<typeof setTimeout> | null = null
  let boundEditor: Editor | undefined = undefined
  let updateCallback: (() => void) | null = null

  function getDefaultLineHeight(): number {
    const el = editor.value?.view?.dom
    if (!el) return DEFAULT_LINE_HEIGHT
    const lineHeight = parseFloat(getComputedStyle(el).lineHeight)
    const fontSize = parseFloat(getComputedStyle(el).fontSize)
    if (!Number.isNaN(lineHeight) && lineHeight > fontSize) return lineHeight
    if (!Number.isNaN(fontSize)) return fontSize * 1.95
    return DEFAULT_LINE_HEIGHT
  }

  /**
   * B14 性能优化：原实现对每个字符位置调用 coordsAtPos（强制同步布局），
   * 长章节每次按键都是 O(n) 重排，是写作页卡顿的主因。
   * 改为按「文本块」采样：每块仅取首尾 2 次 coordsAtPos，再按行高插值出
   * 每块内的逐行 offset，既保持行号与正文的视觉对齐，又把成本从 O(n) 降到 O(块数)。
   */
  function recalculate() {
    if (rafId !== null) cancelAnimationFrame(rafId)

    rafId = requestAnimationFrame(() => {
      const view = editor.value?.view
      if (!view) {
        visualLineCount.value = MIN_LINES
        lineOffsets.value = buildFallbackOffsets(MIN_LINES, getDefaultLineHeight())
        return
      }

      const dom = view.dom
      const containerRect = dom.getBoundingClientRect()
      const baseLineHeight = getDefaultLineHeight()
      const offsets: number[] = []

      view.state.doc.descendants((node, pos) => {
        if (!node.isTextblock) return

        const start = pos + 1
        const end = pos + node.nodeSize - 1

        // 空块仍占一行
        if (start >= end) {
          const last = offsets.length ? offsets[offsets.length - 1] + baseLineHeight : 0
          offsets.push(last)
          return
        }

        let top0: number
        let bottom: number
        try {
          top0 = view.coordsAtPos(start).top
          bottom = view.coordsAtPos(end).top + baseLineHeight
        } catch {
          // 不可见 / 不可计算的位置：用上一条累加行高兜底
          const last = offsets.length ? offsets[offsets.length - 1] + baseLineHeight : 0
          offsets.push(last)
          return
        }

        const blockTop = top0 - containerRect.top
        const lines = Math.max(1, Math.round((bottom - top0) / baseLineHeight))
        for (let i = 0; i < lines; i++) {
          offsets.push(blockTop + i * baseLineHeight)
        }
      })

      const totalCount = Math.max(MIN_LINES, offsets.length)

      visualLineCount.value = totalCount
      lineOffsets.value = padOffsets(offsets, totalCount, baseLineHeight)
    })
  }

  function scheduleRecalculate() {
    if (debounceTimer !== null) clearTimeout(debounceTimer)
    debounceTimer = setTimeout(recalculate, DEBOUNCE_MS)
  }

  function bindEditor(ed: Editor | undefined) {
    if (boundEditor && updateCallback) {
      boundEditor.off('update', updateCallback)
      boundEditor = undefined
      updateCallback = null
    }
    if (ed) {
      updateCallback = scheduleRecalculate
      ed.on('update', updateCallback)
      boundEditor = ed
      scheduleRecalculate()
    }
  }

  onMounted(() => {
    if (scrollContainerRef.value) {
      resizeObserver = new ResizeObserver(scheduleRecalculate)
      resizeObserver.observe(scrollContainerRef.value)
    }
  })

  onUnmounted(() => {
    if (boundEditor && updateCallback) boundEditor.off('update', updateCallback)
    if (resizeObserver) resizeObserver.disconnect()
    if (debounceTimer !== null) clearTimeout(debounceTimer)
    if (rafId !== null) cancelAnimationFrame(rafId)
  })

  watch(
    () => editor.value,
    (ed) => bindEditor(ed),
    { immediate: true },
  )

  return {
    visualLineCount,
    lineOffsets,
    recalculate,
  }
}

function buildFallbackOffsets(count: number, lineHeight: number): number[] {
  const offsets: number[] = []
  for (let i = 0; i < count; i++) {
    offsets.push(i * lineHeight)
  }
  return offsets
}

function padOffsets(actualOffsets: number[], targetCount: number, lineHeight: number): number[] {
  if (actualOffsets.length === 0) {
    return buildFallbackOffsets(targetCount, lineHeight)
  }

  const result = [...actualOffsets]
  const lastOffset = actualOffsets[actualOffsets.length - 1]
  const missing = targetCount - result.length
  for (let i = 1; i <= missing; i++) {
    result.push(lastOffset + i * lineHeight)
  }
  return result
}
