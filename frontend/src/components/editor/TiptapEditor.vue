<template>
  <div class="tiptap-editor">
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
      </div>
      <div class="toolbar-right">
        <span class="word-count">{{ formattedWordCount }} 字</span>
      </div>
    </div>

    <!-- 编辑区域 -->
    <div class="editor-content">
      <div class="editor-wrapper">
        <EditorContent
          v-if="editor"
          :editor="editor"
          class="editor-text"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'
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
} from '@vicons/tabler'
import { useEditor, EditorContent, type Editor } from '@tiptap/vue-3'
import StarterKit from '@tiptap/starter-kit'
import UnderlineExtension from '@tiptap/extension-underline'
import TextAlign from '@tiptap/extension-text-align'
import Placeholder from '@tiptap/extension-placeholder'
import DOMPurify from 'dompurify'

/**
 * TiptapEditor — NexusForge 解耦版富文本编辑器
 *
 * 设计原则（Phase 4 Task 4.1）：
 * - 通过 props/emit 解耦，不依赖 StellarScribe stores/composables
 * - 父组件传入 content（HTML 字符串），编辑器内部变更时 emit('update', html)
 * - 字数统计、撤销/重做、工具栏命令自包含
 * - 行号栏、AI 续写等高级功能暂不移植（后续按需补回）
 */

const props = withDefaults(defineProps<{
  /** 章节内容（HTML 字符串） */
  content?: string
  /** 占位提示文本 */
  placeholder?: string
  /** 只读模式 */
  readonly?: boolean
}>(), {
  content: '',
  placeholder: '开始你的创作...',
  readonly: false,
})

const emit = defineEmits<{
  /** 内容更新时触发（防抖 800ms） */
  (e: 'update', html: string): void
  /** 字数变化时触发 */
  (e: 'word-count', count: number): void
}>()

// ─── 内容消毒 ────────────────────────────────────────────────────────────
const sanitizedContent = computed(() => {
  const raw = props.content || '<p class="paragraph"></p>'
  return DOMPurify.sanitize(raw)
})

// ─── Tiptap 编辑器 ───────────────────────────────────────────────────────
const editor = useEditor({
  content: sanitizedContent.value,
  extensions: [
    StarterKit.configure({ history: { depth: 100 } }),
    UnderlineExtension,
    TextAlign.configure({ types: ['heading', 'paragraph'] }),
    Placeholder.configure({ placeholder: props.placeholder }),
  ],
  editable: !props.readonly,
  editorProps: {
    attributes: {
      class: 'paragraph',
    },
  },
  onUpdate: () => {
    updateWordCount()
    updateUndoRedoState()
    scheduleEmitUpdate()
  },
})

// ─── 字数统计 ────────────────────────────────────────────────────────────
const wordCount = ref(0)

function updateWordCount() {
  if (!editor.value) {
    wordCount.value = 0
    return
  }
  const text = editor.value.state.doc.textContent || ''
  // 中文字符按字计数，英文按单词计数
  const chineseChars = (text.match(/[\u4e00-\u9fa5]/g) || []).length
  const englishWords = (text.replace(/[\u4e00-\u9fa5]/g, ' ').trim().split(/\s+/)).filter(Boolean).length
  wordCount.value = chineseChars + englishWords
  emit('word-count', wordCount.value)
}

const formattedWordCount = computed(() => wordCount.value.toLocaleString())

// ─── 撤销/重做状态 ────────────────────────────────────────────────────────
const canUndo = ref(false)
const canRedo = ref(false)

function updateUndoRedoState() {
  if (!editor.value) return
  canUndo.value = editor.value.can().undo()
  canRedo.value = editor.value.can().redo()
}

// ─── 工具栏命令 ──────────────────────────────────────────────────────────
function execCommand(command: string, value?: string) {
  if (!editor.value) return
  const cmds = editor.value.commands
  switch (command) {
    case 'undo':
      cmds.undo()
      break
    case 'redo':
      cmds.redo()
      break
    case 'bold':
      cmds.toggleBold()
      break
    case 'italic':
      cmds.toggleItalic()
      break
    case 'underline':
      cmds.toggleUnderline()
      break
    case 'strikeThrough':
      cmds.toggleStrike()
      break
    case 'formatBlock':
      // Tiptap 用 setHeading / toggleBlockquote / toggleCodeBlock
      if (value === 'h1') cmds.setHeading({ level: 1 })
      else if (value === 'h2') cmds.setHeading({ level: 2 })
      else if (value === 'h3') cmds.setHeading({ level: 3 })
      else if (value === 'blockquote') cmds.toggleBlockquote()
      else if (value === 'pre') cmds.toggleCodeBlock()
      break
    case 'justifyLeft':
      cmds.setTextAlign('left')
      break
    case 'justifyCenter':
      cmds.setTextAlign('center')
      break
    case 'justifyRight':
      cmds.setTextAlign('right')
      break
  }
  updateUndoRedoState()
}

// ─── 防抖 emit update ────────────────────────────────────────────────────
let emitTimer: ReturnType<typeof setTimeout> | null = null

function scheduleEmitUpdate() {
  if (emitTimer) clearTimeout(emitTimer)
  emitTimer = setTimeout(() => {
    if (editor.value) {
      emit('update', editor.value.getHTML())
    }
    emitTimer = null
  }, 800)
}

// ─── 外部 content 变化时同步编辑器 ────────────────────────────────────────
watch(
  () => props.content,
  (newContent) => {
    if (!editor.value) return
    const currentHtml = editor.value.getHTML()
    const incoming = DOMPurify.sanitize(newContent || '<p class="paragraph"></p>')
    // 避免光标跳动：仅当内容确实不同时才 setContent
    if (currentHtml !== incoming) {
      editor.value.commands.setContent(incoming, false)
      nextTick(() => {
        updateWordCount()
        updateUndoRedoState()
      })
    }
  }
)

// ─── 只读模式切换 ────────────────────────────────────────────────────────
watch(
  () => props.readonly,
  (ro) => {
    editor.value?.setEditable(!ro)
  }
)

onMounted(() => {
  updateWordCount()
  updateUndoRedoState()
})

onUnmounted(() => {
  if (emitTimer) clearTimeout(emitTimer)
  editor.value?.destroy()
})

// 暴露 editor 实例（供父组件高级操作）
defineExpose({ editor })
</script>

<style scoped>
.tiptap-editor {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--nexusforge-editor-paper, #ffffff);
  overflow: hidden;
}

/* ========== 工具栏 ========== */
.toolbar {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  height: 44px;
  border-bottom: 1px solid var(--nexusforge-border-1, rgba(0, 0, 0, 0.09));
  background: var(--nexusforge-editor-paper, #ffffff);
  position: sticky;
  top: 0;
  z-index: 10;
}

.toolbar-left {
  display: flex;
  align-items: center;
  gap: 4px;
}

.toolbar-divider {
  width: 1px;
  height: 16px;
  margin: 0 4px;
  background: var(--nexusforge-border-1, rgba(0, 0, 0, 0.09));
}

.tool-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 4px;
  background: transparent;
  color: var(--nexusforge-text-2, #475569);
  cursor: pointer;
  transition: background-color 0.15s ease, color 0.15s ease;
}

.tool-btn:hover:not(:disabled) {
  background: var(--nexusforge-surface-hover, rgba(0, 0, 0, 0.05));
  color: var(--nexusforge-text-1, #0f172a);
}

.tool-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.tool-icon {
  width: 14px;
  height: 14px;
}

.toolbar-right {
  flex-shrink: 0;
}

.word-count {
  font-family: 'JetBrains Mono', 'Consolas', monospace;
  font-size: 13px;
  color: var(--nexusforge-text-3, #64748b);
  font-variant-numeric: tabular-nums;
}

/* ========== 编辑区域 ========== */
.editor-content {
  flex: 1;
  overflow-y: auto;
  scrollbar-gutter: stable;
}

.editor-wrapper {
  display: flex;
  justify-content: flex-start;
  padding: 48px 16px;
}

.editor-text {
  flex: 1;
  min-height: 100%;
  max-width: 52rem;
}

.editor-text :deep(.ProseMirror) {
  font-family: 'Noto Serif SC', 'Source Han Serif', serif;
  font-size: 16px;
  line-height: 1.8;
  color: var(--nexusforge-text-editor, #1f2937);
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
  color: var(--nexusforge-text-4, #94a3b8);
  pointer-events: none;
  height: 0;
}

.paragraph {
  text-indent: 2em;
  margin: 0;
}
</style>
