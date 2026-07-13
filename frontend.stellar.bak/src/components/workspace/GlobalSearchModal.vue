<template>
  <div v-if="searchStore.visible" class="global-search-modal" @click.self="searchStore.close()">
    <div class="modal-content">
      <div class="modal-header">
        <input
          v-model="searchStore.query"
          class="search-input"
          type="text"
          placeholder="搜索人物/伏笔/设定/章节..."
          @input="onInput"
        />
        <button class="close-btn" @click="searchStore.close()">×</button>
      </div>

      <div v-if="searchStore.loading" class="loading-state">搜索中…</div>

      <div v-else class="results-container">
        <div v-if="hasNoResults" class="empty-state">
          <p v-if="searchStore.query">未找到匹配结果</p>
          <p v-else>输入关键词以搜索</p>
        </div>

        <div v-if="searchStore.results.characters.length" class="result-section">
          <h4 class="section-title">人物 ({{ searchStore.results.characters.length }})</h4>
          <div
            v-for="item in searchStore.results.characters.slice(0, 10)"
            :key="item.id"
            class="result-item"
          >
            <span class="item-name">{{ item.name }}</span>
            <span v-if="item.role" class="item-meta">{{ item.role }}</span>
            <p v-if="item.description" class="item-desc">{{ item.description }}</p>
          </div>
        </div>

        <div v-if="searchStore.results.foreshadows.length" class="result-section">
          <h4 class="section-title">伏笔 ({{ searchStore.results.foreshadows.length }})</h4>
          <div
            v-for="item in searchStore.results.foreshadows.slice(0, 10)"
            :key="item.id"
            class="result-item"
          >
            <span class="item-name">{{ item.title }}</span>
            <span v-if="item.priority" class="item-meta">{{ item.priority }}</span>
            <p v-if="item.description" class="item-desc">{{ item.description }}</p>
          </div>
        </div>

        <div v-if="searchStore.results.facts.length" class="result-section">
          <h4 class="section-title">记忆事实 ({{ searchStore.results.facts.length }})</h4>
          <div
            v-for="item in searchStore.results.facts.slice(0, 10)"
            :key="item.id"
            class="result-item"
          >
            <span class="item-name">{{ item.key }}</span>
            <span v-if="item.value" class="item-desc">{{ item.value }}</span>
          </div>
        </div>

        <div v-if="searchStore.results.settings.length" class="result-section">
          <h4 class="section-title">世界观设定 ({{ searchStore.results.settings.length }})</h4>
          <div
            v-for="item in searchStore.results.settings.slice(0, 10)"
            :key="item.id"
            class="result-item"
          >
            <span class="item-name">{{ item.name }}</span>
            <span v-if="item.setting_type" class="item-meta">{{ item.setting_type }}</span>
            <p v-if="item.description" class="item-desc">{{ item.description }}</p>
          </div>
        </div>

        <div v-if="searchStore.results.chapters.length" class="result-section">
          <h4 class="section-title">章节 ({{ searchStore.results.chapters.length }})</h4>
          <div
            v-for="item in searchStore.results.chapters.slice(0, 10)"
            :key="item.id"
            class="result-item"
          >
            <span class="item-name">第{{ item.number }}章 · {{ item.title }}</span>
            <span v-if="item.status" class="item-meta">{{ item.status }}</span>
            <p v-if="item.outline" class="item-desc">{{ item.outline }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onUnmounted } from 'vue'
import { useSearchStore } from '@/stores/search'
import { useCurrentNovelId } from '@/composables/useCurrentNovelId'

const searchStore = useSearchStore()
const { novelId } = useCurrentNovelId()

const hasNoResults = computed(() => {
  const r = searchStore.results
  return (
    r.characters.length === 0 &&
    r.foreshadows.length === 0 &&
    r.facts.length === 0 &&
    r.settings.length === 0 &&
    r.chapters.length === 0
  )
})

// 防抖 300ms
let debounceTimer: ReturnType<typeof setTimeout> | null = null
function onInput() {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    const q = searchStore.query.trim()
    if (q && novelId.value) {
      searchStore.search(q, novelId.value)
    }
  }, 300)
}

onUnmounted(() => {
  if (debounceTimer) clearTimeout(debounceTimer)
})
</script>

<style scoped>
.global-search-modal {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 80px;
  z-index: 1000;
}

.modal-content {
  width: 640px;
  max-width: 90vw;
  max-height: 70vh;
  background: var(--xy-surface-1);
  border: 1px solid var(--xy-border-1);
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-shadow: 0 12px 40px rgba(0, 0, 0, 0.3);
}

.modal-header {
  display: flex;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid var(--xy-border-1);
  gap: 8px;
}

.search-input {
  flex: 1;
  border: none;
  outline: none;
  background: transparent;
  color: var(--xy-text-1);
  font-size: 15px;
  padding: 8px 4px;
}

.search-input::placeholder {
  color: var(--xy-text-4);
}

.close-btn {
  border: none;
  background: transparent;
  color: var(--xy-text-3);
  font-size: 24px;
  cursor: pointer;
  padding: 4px 8px;
  border-radius: 4px;
}

.close-btn:hover {
  background: var(--xy-surface-hover);
  color: var(--xy-text-1);
}

.loading-state,
.empty-state {
  padding: 32px;
  text-align: center;
  color: var(--xy-text-3);
  font-size: 13px;
}

.results-container {
  flex: 1;
  overflow-y: auto;
  padding: 8px 0;
}

.result-section {
  padding: 8px 16px;
  border-bottom: 1px solid var(--xy-border-1);
}

.result-section:last-child {
  border-bottom: none;
}

.section-title {
  margin: 0 0 8px;
  font-size: 11px;
  font-weight: 600;
  color: var(--xy-text-3);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.result-item {
  padding: 8px 0;
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: 8px;
}

.item-name {
  font-size: 13px;
  font-weight: 500;
  color: var(--xy-text-1);
}

.item-meta {
  font-size: 11px;
  color: var(--xy-text-3);
  padding: 1px 6px;
  border-radius: 4px;
  background: var(--xy-surface-2);
}

.item-desc {
  flex-basis: 100%;
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--xy-text-2);
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
