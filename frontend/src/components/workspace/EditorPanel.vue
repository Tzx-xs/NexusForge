<template>
  <div class="editor-panel">
    <!-- 工具栏 -->
    <div class="toolbar">
      <div class="toolbar-left">
        <button
          class="tool-btn"
          aria-label="撤销"
          :disabled="!canUndo"
          @click="execCommand('undo')"
        >
          <ArrowBackUp class="tool-icon" />
        </button>
        <button
          class="tool-btn"
          aria-label="重做"
          :disabled="!canRedo"
          @click="execCommand('redo')"
        >
          <ArrowForwardUp class="tool-icon" />
        </button>
        <div class="toolbar-divider"></div>
        <button class="tool-btn" aria-label="加粗" @click="execCommand('bold')">
          <Bold class="tool-icon" />
        </button>
        <button class="tool-btn" aria-label="斜体" @click="execCommand('italic')">
          <Italic class="tool-icon" />
        </button>
        <button class="tool-btn" aria-label="下划线" @click="execCommand('underline')">
          <Underline class="tool-icon" />
        </button>
        <button class="tool-btn" aria-label="删除线" @click="execCommand('strikeThrough')">
          <Strikethrough class="tool-icon" />
        </button>
        <div class="toolbar-divider"></div>
        <button class="tool-btn" aria-label="标题1" @click="execCommand('formatBlock', 'h1')">
          <H1 class="tool-icon" />
        </button>
        <button class="tool-btn" aria-label="标题2" @click="execCommand('formatBlock', 'h2')">
          <H2 class="tool-icon" />
        </button>
        <button class="tool-btn" aria-label="标题3" @click="execCommand('formatBlock', 'h3')">
          <H3 class="tool-icon" />
        </button>
        <div class="toolbar-divider"></div>
        <button
          class="tool-btn"
          aria-label="引用"
          @click="execCommand('formatBlock', 'blockquote')"
        >
          <Quote class="tool-icon" />
        </button>
        <button class="tool-btn" aria-label="代码" @click="execCommand('formatBlock', 'pre')">
          <Code class="tool-icon" />
        </button>
        <div class="toolbar-divider"></div>
        <button class="tool-btn" aria-label="左对齐" @click="execCommand('justifyLeft')">
          <AlignLeft class="tool-icon" />
        </button>
        <button class="tool-btn" aria-label="居中" @click="execCommand('justifyCenter')">
          <AlignCenter class="tool-icon" />
        </button>
        <button class="tool-btn" aria-label="右对齐" @click="execCommand('justifyRight')">
          <AlignRight class="tool-icon" />
        </button>
        <div class="toolbar-divider"></div>
        <button class="ai-continue-btn" :disabled="isAiGenerating" @click="handleAiContinue">
          <Bulb class="ai-icon" />
          <span>{{ isAiGenerating ? '生成中...' : 'AI 续写' }}</span>
        </button>
      </div>
      <div class="toolbar-right">
        <span class="word-count">{{ formattedWordCount }} 字</span>
      </div>
    </div>

    <!-- 编辑区域 -->
    <div ref="editorContentRef" class="editor-content">
      <div class="editor-wrapper">
        <div class="editor-inner">
          <!-- 行号栏 -->
          <div class="line-numbers">
            <div
              v-for="n in visualLineCount"
              :key="n"
              class="line-number"
              :style="lineNumberStyle(n - 1)"
            >
              {{ n }}
            </div>
          </div>
          <!-- Tiptap 编辑器 -->
          <EditorContent
            v-if="editor"
            :editor="editor"
            class="editor-text"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick, type Ref } from 'vue'
import {
  ArrowBackUp,
  ArrowForwardUp,
  Bold,
  Italic,
  Underline,
  Strikethrough,
  H1,
  H2,
  H3,
  Quote,
  Code,
  AlignLeft,
  AlignCenter,
  AlignRight,
  Bulb,
} from '@vicons/tabler'
import { useEditor, EditorContent, type Editor } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import UnderlineExtension from '@tiptap/extension-underline'
import TextAlign from '@tiptap/extension-text-align'
import Placeholder from '@tiptap/extension-placeholder'
import { useChapterStore } from '@/stores/chapter'
import { useEditorStatusStore } from '@/stores/editorStatus'
import DOMPurify from 'dompurify'
import { useWordCount } from '@/composables/useWordCount'
import { useEditorCommands } from '@/composables/useEditorCommands'
import { useAutoSave } from '@/composables/useAutoSave'
import { useAiGenerate } from '@/composables/useAiGenerate'
import { useVisualLineCount } from '@/composables/useVisualLineCount'

const chapterStore = useChapterStore()
const editorStatusStore = useEditorStatusStore()

const chapterContent = computed(() => {
  const raw = chapterStore.currentChapter?.content || '<p class="paragraph"></p>'
  return DOMPurify.sanitize(raw)
})

const editor = useEditor({
  content: chapterContent.value,
  extensions: [
    StarterKit.configure({ history: { depth: 100 } }),
    UnderlineExtension,
    TextAlign.configure({ types: ['heading', 'paragraph'] }),
    Placeholder.configure({ placeholder: '开始你的创作...' }),
  ],
  editorProps: {
    attributes: {
      class: 'paragraph',
    },
  },
  onUpdate: () => {
    // B14：长文下改为防抖统计，避免每次按键全量遍历文档
    updateWordCountDebounced()
    updateUndoRedoState()
    updateCursor()
    saveContent()
  },
  onSelectionUpdate: () => {
    updateCursor()
  },
  onBlur: () => {
    saveContent()
  },
})

const editorRef = ref<HTMLDivElement | null>(null)
const editorContentRef = ref<HTMLElement | null>(null)

const { visualLineCount, lineOffsets } = useVisualLineCount(
  editor as unknown as Ref<Editor | undefined>,
  editorContentRef,
)

function lineNumberStyle(index: number) {
  const next = lineOffsets.value[index + 1]
  const current = lineOffsets.value[index]
  let height: number
  if (next !== undefined && current !== undefined) {
    height = next - current
  } else {
    const prev = lineOffsets.value[index - 1]
    height = current !== undefined && prev !== undefined ? current - prev : 31.2
  }
  return {
    height: `${height}px`,
    lineHeight: `${height}px`,
  }
}

const { wordCount, updateWordCount, updateWordCountDebounced } = useWordCount(
  editorRef,
  editor as unknown as { value: Editor | null }
)

const { canUndo, canRedo, execCommand, updateUndoRedoState } = useEditorCommands(
  editorRef,
  () => {
    updateWordCount()
    saveContent()
  },
  editor as unknown as { value: Editor | null }
)

const { saveContent } = useAutoSave(
  editorRef,
  () => chapterStore.currentChapter,
  (id, data) => chapterStore.updateChapter(id, data),
  2000,
  () => editor.value?.getHTML() || ''
)

const { isAiGenerating, handleAiContinue } = useAiGenerate(
  editorRef,
  () => {
    saveContent()
    updateWordCount()
  },
  editor as unknown as { value: Editor | null }
)

const formattedWordCount = computed(() => {
  return wordCount.value.toLocaleString()
})

function computeCursorPosition(): { line: number; col: number } {
  if (!editor.value) return { line: 1, col: 1 }
  const { from } = editor.value.state.selection
  const textBefore = editor.value.state.doc.textBetween(0, from, '\n')
  const lines = textBefore.split('\n')
  return { line: lines.length, col: lines[lines.length - 1].length + 1 }
}

function updateCursor() {
  const { line, col } = computeCursorPosition()
  editorStatusStore.setCursor(line, col)
}

// 同步 editorRef 指向 Tiptap DOM（用于 composables 兼容）
watch(
  editor,
  (ed) => {
    editorRef.value = (ed?.view.dom as HTMLDivElement) || null
  },
  { immediate: true }
)

// 章节切换时同步内容
watch(
  () => chapterStore.currentChapter?.id,
  () => {
    if (editor.value) {
      editor.value.commands.setContent(chapterContent.value)
      nextTick(() => {
        updateWordCount()
        updateCursor()
      })
    }
  }
)

onMounted(() => {
  updateWordCount()
  updateCursor()
})

onUnmounted(() => {
  editor.value?.destroy()
})

// 暴露 editor 实例给测试
defineExpose({ editor })
</script>

<style scoped>
.editor-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--xy-editor-paper);
  overflow: hidden;
}

/* ========== 工具栏 ========== */
.toolbar {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--xy-space-4);
  height: var(--xy-toolbar-h);
  border-bottom: var(--xy-border-w-1) solid var(--xy-border-1);
  background: var(--xy-editor-paper);
  position: sticky;
  top: 0;
  z-index: var(--xy-z-sticky);
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: var(--xy-space-1);
}

.toolbar-divider {
  width: 1px;
  height: 16px;
  margin: 0 var(--xy-space-1);
  background: var(--xy-border-1);
}

.tool-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  border-radius: var(--xy-radius-sm);
  background: transparent;
  color: var(--xy-text-2);
  cursor: pointer;
  transition:
    background-color var(--xy-dur-sm) ease,
    color var(--xy-dur-sm) ease;
}

.tool-btn:hover {
  background: var(--xy-surface-hover);
  color: var(--xy-text-1);
}

.tool-icon {
  width: 14px;
  height: 14px;
}

.ai-continue-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 4px 10px;
  height: 28px;
  border: none;
  border-radius: var(--xy-radius-sm);
  background: var(--xy-brand-500);
  color: var(--xy-text-inverse);
  font-size: var(--xy-fs-sm);
  font-weight: var(--xy-fw-med);
  font-family: var(--xy-font-sans);
  cursor: pointer;
  white-space: nowrap;
  transition: background-color var(--xy-dur-sm) ease;
}

.ai-continue-btn:hover {
  background: var(--xy-brand-400);
}

.ai-icon {
  width: 12px;
  height: 12px;
}

.toolbar-right {
  flex-shrink: 0;
}

.word-count {
  font-family: var(--xy-font-mono);
  font-size: var(--xy-fs-sm);
  color: var(--xy-text-3);
  font-variant-numeric: tabular-nums;
}

/* ========== 编辑区域 ========== */
.editor-content {
  flex: 1;
  overflow-y: auto;
  scrollbar-gutter: stable;
}

.editor-content::-webkit-scrollbar {
  width: 6px;
}

.editor-content::-webkit-scrollbar-track {
  background: transparent;
}

.editor-content::-webkit-scrollbar-thumb {
  background: color-mix(in srgb, var(--xy-brand-500) 20%, transparent);
  border-radius: 3px;
}

.editor-content::-webkit-scrollbar-thumb:hover {
  background: color-mix(in srgb, var(--xy-brand-500) 35%, transparent);
}

.editor-wrapper {
  display: flex;
  justify-content: flex-start;
  padding: 48px 16px;
}

.editor-inner {
  display: flex;
  width: 100%;
}

/* 行号栏 */
/* 行号栏：字号与正文保持一致，使首行基线对齐 */
.line-numbers {
  flex-shrink: 0;
  width: 44px;
  font-family: var(--xy-font-mono);
  font-size: var(--xy-fs-editor);
  line-height: var(--xy-lh-editor);
  color: var(--xy-text-4);
  text-align: left;
  padding: 0 10px 0 0;
  user-select: none;
}

.line-number {
  box-sizing: border-box;
  line-height: var(--xy-lh-editor);
}

/* Tiptap ProseMirror 编辑区 */
.editor-text {
  flex: 1;
  min-height: 100%;
  max-width: 52rem;
}

.editor-text :deep(.ProseMirror) {
  font-family: var(--xy-font-serif);
  font-size: var(--xy-fs-editor);
  line-height: var(--xy-lh-editor);
  color: var(--xy-text-editor);
  outline: none;
  min-height: 100%;
  cursor: text;
}

.editor-text :deep(.ProseMirror:focus) {
  outline: none;
}

.editor-text :deep(.ProseMirror p) {
  text-indent: 2em;
  margin: 0;
}

.editor-text :deep(.ProseMirror .is-editor-empty:first-child::before) {
  content: attr(data-placeholder);
  float: left;
  color: var(--xy-text-4);
  pointer-events: none;
  height: 0;
}

.chapter-title {
  font-family: var(--xy-font-sans);
  font-size: 28px;
  font-weight: var(--xy-fw-bold);
  line-height: 1.3;
  color: var(--xy-brand-600);
  text-decoration: underline;
  text-decoration-color: var(--xy-brand-500);
  text-underline-offset: 6px;
  text-decoration-thickness: 2px;
  margin: 0 0 32px 0;
  word-break: keep-all;
  overflow-wrap: break-word;
}

.paragraph {
  text-indent: 2em;
  margin: 0;
}

.active-line {
  background: var(--xy-active-line);
  border-radius: 2px;
  margin: 0 -8px;
  padding: 0 8px;
}
</style>
