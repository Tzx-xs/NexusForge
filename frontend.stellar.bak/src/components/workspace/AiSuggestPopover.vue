<template>
  <div v-if="visible" class="ai-suggest-content">
    <div class="ai-suggest-header">
      <span class="ai-suggest-title">AI 写作建议</span>
      <button class="close-btn" aria-label="关闭" @click="handleClose">×</button>
    </div>
    <div class="ai-suggest-body">
      <div v-if="isLoading" class="loading-indicator">正在生成建议...</div>
      <div class="suggest-text">{{ suggestText }}</div>
      <div v-if="error" class="error-message">{{ error }}</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, onUnmounted } from 'vue'
import { useChapterStore } from '@/stores/chapter'
import { streamAiSuggest } from '@/api/aiSuggest'

const props = defineProps<{ visible: boolean }>()
const emit = defineEmits<{ 'update:visible': [value: boolean] }>()

const chapterStore = useChapterStore()
const suggestText = ref('')
const isLoading = ref(false)
const error = ref<string | null>(null)

let abortController: AbortController | null = null

async function startSuggest(): Promise<void> {
  const chapterId = chapterStore.currentChapter?.id
  if (!chapterId) {
    error.value = '未找到当前章节，无法生成建议'
    return
  }

  isLoading.value = true
  suggestText.value = ''
  error.value = null
  abortController = new AbortController()

  try {
    for await (const evt of streamAiSuggest(chapterId, abortController.signal)) {
      if (evt.type === 'token') {
        suggestText.value += (evt.data.delta as string) || ''
      } else if (evt.type === 'complete') {
        isLoading.value = false
      } else if (evt.type === 'error') {
        error.value = (evt.data.message as string) || '生成失败'
        isLoading.value = false
      }
    }
  } catch (err: unknown) {
    const e = err as { name?: string; message?: string }
    if (e?.name !== 'AbortError') {
      error.value = e?.message || '网络错误，生成失败'
    }
  } finally {
    isLoading.value = false
    abortController = null
  }
}

function handleClose(): void {
  if (abortController) {
    abortController.abort()
  }
  emit('update:visible', false)
}

watch(
  () => props.visible,
  (newVal) => {
    if (newVal) {
      void startSuggest()
    } else if (abortController) {
      abortController.abort()
    }
  },
  { immediate: true }
)

onUnmounted(() => {
  if (abortController) {
    abortController.abort()
  }
})
</script>

<style scoped>
.ai-suggest-content {
  position: fixed;
  top: 80px;
  right: 24px;
  width: 380px;
  max-height: 60vh;
  background: var(--xy-surface-1, #1a1535);
  border: 1px solid var(--xy-border-1, rgba(255, 255, 255, 0.08));
  border-radius: 12px;
  box-shadow: var(--xy-shadow-lg, 0 8px 32px rgba(0, 0, 0, 0.4));
  z-index: 1000;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.ai-suggest-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 16px;
  border-bottom: 1px solid var(--xy-border-1, rgba(255, 255, 255, 0.08));
}

.ai-suggest-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--xy-text-1, #f0edf8);
}

.close-btn {
  background: none;
  border: none;
  color: var(--xy-text-2, #a89ec9);
  font-size: 20px;
  cursor: pointer;
  padding: 0 4px;
  line-height: 1;
}

.close-btn:hover {
  color: var(--xy-text-1, #f0edf8);
}

.ai-suggest-body {
  padding: 16px;
  overflow-y: auto;
  flex: 1;
}

.loading-indicator {
  color: var(--xy-text-2, #a89ec9);
  font-size: 13px;
  margin-bottom: 8px;
}

.suggest-text {
  color: var(--xy-text-1, #f0edf8);
  font-size: 14px;
  line-height: 1.7;
  white-space: pre-wrap;
  word-break: break-word;
}

.error-message {
  color: var(--xy-error, #ff6b6b);
  font-size: 13px;
  margin-top: 8px;
}
</style>
