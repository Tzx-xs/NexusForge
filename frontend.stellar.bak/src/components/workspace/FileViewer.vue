<template>
  <div class="file-viewer">
    <div class="file-toolbar">
      <span v-if="title" class="file-title">{{ title }}</span>
      <span v-else class="file-title-placeholder">未选择文件</span>
      <button
        v-if="hasContent"
        class="file-action-btn secondary"
        @click="showSource = !showSource"
      >
        {{ showSource ? '预览' : '源码' }}
      </button>
    </div>

    <div v-if="!hasContent" class="file-empty">
      <FileText class="empty-icon" />
      <p class="empty-title">{{ title ? '暂无内容' : '在左侧选择章节或设定文件' }}</p>
      <p class="empty-desc">{{ title ? '可在编辑器中开始创作' : '支持章节正文、人物档案与世界观设定' }}</p>
    </div>

    <div v-else class="file-content">
      <div v-if="isMarkdown && !showSource" class="markdown-body" v-html="sanitizedHtml" />
      <pre v-else class="plain-text"><code>{{ content }}</code></pre>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import { FileText } from '@vicons/tabler'

const props = defineProps<{
  title?: string
  content?: string
  mode?: 'markdown' | 'plain'
}>()

const showSource = ref(false)

const hasContent = computed(() => typeof props.content === 'string' && props.content.length > 0)

const isMarkdown = computed(() => props.mode === 'markdown')

const sanitizedHtml = computed(() => {
  if (!isMarkdown.value || showSource.value) return ''
  const raw = marked.parse(props.content || '', { async: false }) as string
  return DOMPurify.sanitize(raw)
})
</script>

<style scoped>
.file-viewer {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--xy-editor-paper);
  overflow: hidden;
}

.file-toolbar {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--xy-space-2);
  padding: var(--xy-space-3) var(--xy-space-4);
  border-bottom: var(--xy-border-w-1) solid var(--xy-border-1);
  background: var(--xy-surface-1);
}

.file-title {
  font-size: var(--xy-fs-sm);
  font-weight: var(--xy-fw-sb);
  color: var(--xy-text-1);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.file-title-placeholder {
  font-size: var(--xy-fs-sm);
  color: var(--xy-text-3);
}

.file-action-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 5px 10px;
  border: none;
  border-radius: var(--xy-radius-sm);
  background: var(--xy-surface-2);
  color: var(--xy-text-1);
  font-size: var(--xy-fs-xs);
  cursor: pointer;
  transition: background-color var(--xy-dur-sm) ease;
}

.file-action-btn:hover {
  background: var(--xy-surface-hover);
}

.file-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--xy-space-3);
  padding: var(--xy-space-8);
  color: var(--xy-text-3);
}

.empty-icon {
  width: 44px;
  height: 44px;
  color: var(--xy-brand-500);
  opacity: 0.7;
}

.empty-title {
  font-size: var(--xy-fs-base);
  color: var(--xy-text-1);
  margin: 0;
}

.empty-desc {
  font-size: var(--xy-fs-sm);
  color: var(--xy-text-3);
  margin: 0;
}

.file-content {
  flex: 1;
  overflow-y: auto;
  padding: var(--xy-space-6);
}

.plain-text {
  margin: 0;
  font-family: var(--xy-font-mono);
  font-size: var(--xy-fs-sm);
  line-height: var(--xy-lh-editor);
  color: var(--xy-text-1);
  white-space: pre-wrap;
  word-break: break-word;
}

.markdown-body {
  font-family: var(--xy-font-serif);
  font-size: var(--xy-fs-base);
  line-height: var(--xy-lh-editor);
  color: var(--xy-text-1);
}

.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3),
.markdown-body :deep(h4),
.markdown-body :deep(h5),
.markdown-body :deep(h6) {
  font-family: var(--xy-font-sans);
  color: var(--xy-text-1);
  margin: 1.5em 0 0.5em;
}

.markdown-body :deep(p) {
  margin: 0.8em 0;
}

.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  padding-left: 1.5em;
  margin: 0.8em 0;
}

.markdown-body :deep(code) {
  font-family: var(--xy-font-mono);
  background: var(--xy-surface-2);
  padding: 2px 6px;
  border-radius: var(--xy-radius-sm);
}

.markdown-body :deep(pre) {
  background: var(--xy-surface-2);
  padding: var(--xy-space-3);
  border-radius: var(--xy-radius-md);
  overflow-x: auto;
}

.markdown-body :deep(pre code) {
  background: transparent;
  padding: 0;
}

.markdown-body :deep(blockquote) {
  border-left: 4px solid var(--xy-brand-500);
  margin: 0.8em 0;
  padding-left: var(--xy-space-3);
  color: var(--xy-text-2);
}
</style>
