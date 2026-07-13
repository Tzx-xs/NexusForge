<template>
  <div class="chapter-rail">
    <div class="search-box">
      <Search class="search-icon" />
      <input v-model="searchQuery" type="text" class="search-input" placeholder="搜索章节..." />
    </div>

    <div class="volume-list">
      <template v-if="volumes.length > 0">
        <div
          v-for="volume in volumes"
          :key="volume.id"
          class="volume-block"
        >
          <div class="volume-header" @click="toggleVolume(volume.id)">
            <ChevronDown v-if="expandedVolumes.has(volume.id)" class="chevron-icon" />
            <ChevronRight v-else class="chevron-icon" />
            <span class="volume-name">{{ volume.name }}</span>
            <span class="volume-count">{{ volume.chapters.length }} 章</span>
          </div>

          <div v-if="expandedVolumes.has(volume.id)" class="volume-chapters">
            <div
              v-for="chapter in volume.chapters"
              :key="chapter.id"
              class="chapter-item"
              :class="{ 'chapter-active': isActiveChapter(chapter.id) }"
              @click.stop="selectChapter(chapter)"
            >
              <span
                class="status-dot"
                :class="{
                  'status-completed': chapter.status === 'completed',
                  'status-planned': chapter.status === 'planned',
                  'status-draft': chapter.status === 'draft',
                }"
              ></span>
              <span class="chapter-name">{{ chapter.name }}</span>
              <span v-if="chapter.wordCount" class="chapter-wordcount">
                {{ chapter.wordCount }}
              </span>
            </div>
          </div>
        </div>
      </template>
      <div v-else class="empty-hint">暂无章节</div>
    </div>

    <button class="add-chapter-btn" @click="handleAddChapter">
      <Plus class="plus-icon" />
      <span>新增章节</span>
    </button>

    <XyDialog
      v-model="addDialogVisible"
      title="新增章节"
      confirm-text="创建"
      cancel-text="取消"
      @confirm="confirmAddChapter"
    >
      <div class="add-chapter-form">
        <label class="add-chapter-label" for="chapter-title-input">章节标题</label>
        <input
          id="chapter-title-input"
          v-model="newChapterTitle"
          type="text"
          class="add-chapter-input"
          placeholder="请输入章节标题"
          @keydown.enter="confirmAddChapter"
        />
      </div>
    </XyDialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Search, ChevronRight, ChevronDown, Plus } from '@vicons/tabler'
import { useChapterStore } from '@/stores/chapter'
import { useDocViewerStore } from '@/stores/docViewer'
import { toast } from '@/utils/toast'
import { XyDialog } from '@/components/common'
import type { Chapter } from '@/api/chapters'
import { mapStatus as mapStatusFn, type ChapterStatusKey } from './chapterStatus'

const props = defineProps<{ novelId?: string }>()

const router = useRouter()
const route = useRoute()
const chapterStore = useChapterStore()
const docViewerStore = useDocViewerStore()

const searchQuery = ref('')
const chapterStoreRef = chapterStore
const mapStatus = mapStatusFn
const addDialogVisible = ref(false)
const newChapterTitle = ref('新章节')

interface ChapterNode {
  id: string
  name: string
  status?: ChapterStatusKey
  wordCount?: string
  raw: Chapter
}

interface VolumeNode {
  id: string
  name: string
  chapters: ChapterNode[]
}

function formatWordCount(count: number): string {
  if (count === 0) return ''
  if (count >= 1000) return `${(count / 1000).toFixed(1)}k字`
  return `${count}字`
}

function numberToChinese(n: number): string {
  const digits = ['零', '一', '二', '三', '四', '五', '六', '七', '八', '九']
  if (n <= 10) return digits[n] || String(n)
  if (n < 20) return '十' + (n % 10 === 0 ? '' : digits[n % 10])
  const tens = Math.floor(n / 10)
  const ones = n % 10
  return digits[tens] + '十' + (ones === 0 ? '' : digits[ones])
}

const chapterNodes = computed<ChapterNode[]>(() => {
  const query = searchQuery.value.trim().toLowerCase()
  let list = chapterStoreRef.chapters.map((ch: Chapter) => ({
    id: ch.id,
    name: `第${ch.number}章 ${ch.title}`,
    status: mapStatus(ch.status),
    wordCount: formatWordCount(ch.word_count),
    raw: ch,
  }))
  if (query) {
    list = list.filter((ch) => ch.name.toLowerCase().includes(query))
  }
  return list
})

const CHAPTERS_PER_VOLUME = 10

const volumes = computed<VolumeNode[]>(() => {
  const nodes = chapterNodes.value
  if (nodes.length === 0) return []
  const map = new Map<number, ChapterNode[]>()
  nodes.forEach((node) => {
    const volumeIndex = Math.max(0, Math.floor((node.raw.number - 1) / CHAPTERS_PER_VOLUME))
    if (!map.has(volumeIndex)) map.set(volumeIndex, [])
    map.get(volumeIndex)!.push(node)
  })
  return Array.from(map.entries())
    .sort((a, b) => a[0] - b[0])
    .map(([index, chapters]) => ({
      id: `volume-${index}`,
      name: `第${numberToChinese(index + 1)}卷`,
      chapters: chapters.sort((a, b) => a.raw.number - b.raw.number),
    }))
})

const expandedVolumes = reactive(new Set<string>())

function toggleVolume(id: string) {
  if (expandedVolumes.has(id)) {
    expandedVolumes.delete(id)
  } else {
    expandedVolumes.add(id)
  }
}

function isActiveChapter(chapterId: string): boolean {
  if (docViewerStore.selectedType === 'chapter') {
    return docViewerStore.selectedId === chapterId
  }
  return route.params.chapterId === chapterId
}

async function selectChapter(chapter: ChapterNode) {
  docViewerStore.selectChapter(chapter.raw)
  const novelId = props.novelId || (route.params.novelId as string)
  if (novelId) {
    router.push({ name: 'writing', params: { novelId, chapterId: chapter.id } })
  }
}

function handleAddChapter() {
  newChapterTitle.value = '新章节'
  addDialogVisible.value = true
}

async function confirmAddChapter() {
  const novelId = props.novelId || (route.params.novelId as string)
  if (!novelId) {
    toast.error('未识别到小说 ID，无法新增章节')
    addDialogVisible.value = false
    return
  }
  const title = newChapterTitle.value.trim() || '新章节'
  addDialogVisible.value = false
  try {
    const created = await chapterStoreRef.createChapter(novelId, { title })
    toast.success('章节已创建')
    await selectChapter({
      id: created.id,
      name: `第${created.number}章 ${created.title}`,
      status: 'draft',
      raw: created,
    })
  } catch (e: unknown) {
    const err = e as { message?: string }
    toast.error(err?.message || '新增章节失败')
  }
}

onMounted(() => {
  if (props.novelId) {
    chapterStoreRef.fetchChapters(props.novelId)
  }
})
</script>

<style scoped>
.chapter-rail {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--xy-surface-1);
  font-family: var(--xy-font-sans);
  overflow: hidden;
}

/* ========== 搜索框 ========== */
.search-box {
  display: flex;
  align-items: center;
  gap: var(--xy-space-2);
  margin: var(--xy-space-3);
  padding: 0 var(--xy-space-3);
  height: 32px;
  background: var(--xy-surface-2);
  border: var(--xy-border-w-1) solid var(--xy-border-1);
  border-radius: var(--xy-radius-sm);
  flex-shrink: 0;
  transition:
    border-color 150ms ease,
    box-shadow 150ms ease;
}

.search-box:focus-within {
  border-color: var(--xy-border-focus);
  box-shadow: var(--xy-shadow-focus-ring);
}

.search-icon {
  width: 14px;
  height: 14px;
  color: var(--xy-text-3);
  flex-shrink: 0;
}

.search-input {
  flex: 1;
  background: transparent;
  border: none;
  outline: none;
  font-size: var(--xy-fs-sm);
  color: var(--xy-text-1);
  font-family: var(--xy-font-sans);
}

.search-input::placeholder {
  color: var(--xy-text-3);
}

/* ========== 卷列表 ========== */
.volume-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 var(--xy-space-2) var(--xy-space-3);
}

.volume-list::-webkit-scrollbar {
  width: 5px;
}

.volume-list::-webkit-scrollbar-track {
  background: transparent;
}

.volume-list::-webkit-scrollbar-thumb {
  background: rgba(124, 108, 191, 0.2);
  border-radius: 3px;
}

.volume-list::-webkit-scrollbar-thumb:hover {
  background: rgba(124, 108, 191, 0.35);
}

.volume-block {
  display: flex;
  flex-direction: column;
}

.volume-header {
  display: flex;
  align-items: center;
  gap: var(--xy-space-1);
  padding: var(--xy-space-2);
  border-radius: var(--xy-radius-xs);
  cursor: pointer;
  transition: background-color 150ms ease;
  min-height: 32px;
}

.volume-header:hover {
  background: var(--xy-surface-hover);
}

.chevron-icon {
  width: 13px;
  height: 13px;
  color: var(--xy-text-4);
  flex-shrink: 0;
}

.volume-name {
  flex: 1;
  font-size: var(--xy-fs-sm);
  font-weight: var(--xy-fw-sb);
  color: var(--xy-text-1);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.volume-count {
  font-size: 10px;
  color: var(--xy-text-4);
  flex-shrink: 0;
}

.volume-chapters {
  display: flex;
  flex-direction: column;
  padding-left: var(--xy-space-5);
}

.chapter-item {
  display: flex;
  align-items: center;
  gap: var(--xy-space-2);
  padding: var(--xy-space-1) var(--xy-space-2);
  border-radius: var(--xy-radius-xs);
  cursor: pointer;
  transition: background-color 150ms ease;
  min-height: 28px;
}

.chapter-item:hover {
  background: var(--xy-surface-hover);
}

.chapter-active {
  background: var(--xy-brand-100);
}

.chapter-active:hover {
  background: var(--xy-brand-100);
}

.chapter-active .chapter-name {
  color: var(--xy-brand-600);
  font-weight: var(--xy-fw-med);
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
}

.status-completed {
  background: var(--xy-success);
}

.status-current {
  background: var(--xy-brand-500);
  box-shadow: 0 0 0 3px rgba(124, 108, 191, 0.2);
}

.status-draft {
  background: var(--xy-text-3);
}

.status-planned {
  background: var(--xy-warning);
  box-shadow: 0 0 0 3px rgba(245, 158, 11, 0.18);
}

.chapter-name {
  flex: 1;
  font-size: var(--xy-fs-sm);
  color: var(--xy-text-2);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.chapter-wordcount {
  font-size: 10px;
  color: var(--xy-text-4);
  font-family: var(--xy-font-mono);
  flex-shrink: 0;
}

.empty-hint {
  padding: var(--xy-space-8) var(--xy-space-2);
  text-align: center;
  color: var(--xy-text-4);
  font-size: var(--xy-fs-xs);
}

/* ========== 新增章节按钮 ========== */
.add-chapter-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--xy-space-2);
  margin: var(--xy-space-3);
  padding: var(--xy-space-2);
  background: transparent;
  border: 1px dashed var(--xy-border-2);
  border-radius: var(--xy-radius-sm);
  color: var(--xy-text-3);
  font-size: var(--xy-fs-sm);
  cursor: pointer;
  transition: all 150ms ease;
  flex-shrink: 0;
}

.add-chapter-btn:hover {
  border-color: var(--xy-brand-500);
  color: var(--xy-brand-600);
  background: var(--xy-brand-50);
}

.plus-icon {
  width: 14px;
  height: 14px;
}

/* ========== 新增章节弹窗 ========== */
.add-chapter-form {
  display: flex;
  flex-direction: column;
  gap: var(--xy-space-2);
}

.add-chapter-label {
  font-size: var(--xy-fs-sm);
  color: var(--xy-text-2);
}

.add-chapter-input {
  width: 100%;
  height: 36px;
  padding: 0 var(--xy-space-3);
  border: var(--xy-border-w-1) solid var(--xy-border-1);
  border-radius: var(--xy-radius-md);
  background: var(--xy-surface-1);
  color: var(--xy-text-1);
  font-size: var(--xy-fs-base);
  outline: none;
  transition:
    border-color 150ms ease,
    box-shadow 150ms ease;
}

.add-chapter-input:focus {
  border-color: var(--xy-brand-500);
  box-shadow: var(--xy-shadow-focus-ring);
}
</style>
