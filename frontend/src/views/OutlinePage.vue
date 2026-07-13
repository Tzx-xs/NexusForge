<template>
  <div class="outline-page">
    <div class="chapter-rail">
      <div class="rail-header">
        <h3>章节</h3>
      </div>
      <div class="chapter-list">
        <div
          v-for="ch in chapters"
          :key="ch.id"
          class="chapter-item"
          :class="{ active: selectedId === ch.id }"
          @click="selectChapter(ch)"
        >
          <span class="dot" :class="ch.status"></span>
          <span class="title">{{ ch.title }}</span>
          <button class="chapter-delete-btn" title="删除章节" @click.stop="handleDeleteChapter(ch)">
            <Trash class="chapter-delete-icon" />
          </button>
        </div>
      </div>
      <div class="rail-footer">
        <n-button block size="small" :loading="creating" @click="handleCreateChapter">
          <template #icon>
            <n-icon :component="Plus" />
          </template>
          新建章节
        </n-button>
      </div>
    </div>
    <div class="outline-main">
      <div class="outline-toolbar">
        <div class="view-toggle">
          <button
            class="toggle-btn"
            :class="{ active: viewMode === 'list' }"
            @click="viewMode = 'list'"
          >
            <List size="14" />
            列表
          </button>
          <button
            class="toggle-btn"
            :class="{ active: viewMode === 'dag' }"
            @click="viewMode = 'dag'"
          >
            <GitBranch size="14" />
            DAG
          </button>
        </div>
      </div>

      <div v-if="viewMode === 'list'" class="outline-editor">
        <div v-if="selectedChapter" class="editor-content">
          <h2>{{ selectedChapter.title }}</h2>
          <n-input
            v-model:value="editOutline"
            type="textarea"
            class="outline-textarea"
            :autosize="{ minRows: 6 }"
            placeholder="暂无章纲，可在右侧点击生成，或在此手动编辑后保存"
            :disabled="outlineSaving"
          />
        </div>
        <div v-else class="empty-state">
          <n-icon :component="FileText" :size="48" color="#4e4768" />
          <p>选择一个章节查看章纲</p>
        </div>
      </div>

      <div v-if="viewMode === 'dag'" class="dag-container">
        <OutlineDag :novel-id="novelId" />
      </div>

      <div v-if="viewMode === 'list'" class="outline-actions">
        <n-button
          type="primary"
          :loading="generating"
          :disabled="!selectedChapter"
          @click="handleGenerateOutline"
        >
          <template #icon>
            <n-icon :component="Bulb" />
          </template>
          生成章纲
        </n-button>
        <n-button
          type="primary"
          ghost
          :loading="outlineSaving"
          :disabled="!selectedChapter"
          @click="handleSaveOutline"
        >
          <template #icon>
            <n-icon :component="DeviceFloppy" />
          </template>
          保存章纲
        </n-button>
      </div>
    </div>

    <!-- 创建章节弹窗 -->
    <n-modal
      v-model:show="createChapterVisible"
      preset="card"
      title="新建章节"
      style="width: 420px; max-width: 92vw"
    >
      <n-form label-placement="top">
        <n-form-item label="章节标题">
          <n-input
            v-model:value="createChapterTitle"
            placeholder="请输入章节标题"
            @keydown.enter="submitCreateChapter"
          />
        </n-form-item>
      </n-form>
      <template #footer>
        <div class="modal-footer">
          <n-button @click="createChapterVisible = false">取消</n-button>
          <n-button type="primary" :loading="creating" @click="submitCreateChapter">
            创建
          </n-button>
        </div>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { NButton, NIcon, NModal, NForm, NFormItem, NInput, useMessage } from 'naive-ui'
import { Plus, FileText, Bulb, List, GitBranch, Trash, DeviceFloppy } from '@vicons/tabler'
import { useRoute } from 'vue-router'
import { useChapterStore } from '@/stores/chapter'
import { generateOutline } from '@/api/chapters'
import OutlineDag from '@/components/outline/OutlineDag.vue'

const route = useRoute()
const chapterStore = useChapterStore()
const message = useMessage()

const novelId = computed(() => String(route.params.novelId || ''))
const viewMode = ref<'list' | 'dag'>('list')
const creating = ref(false)
const generating = ref(false)
const outlineSaving = ref(false)

const chapters = computed(() => {
  if (chapterStore.chapters.length > 0) {
    return chapterStore.chapters.map((c) => ({
      id: c.id,
      title: c.title,
      status: c.status,
      outline: c.outline,
    }))
  }
  return []
})

type ChapterListItem = (typeof chapters.value)[number]

const selectedId = ref<string | null>(null)
const selectedChapter = computed<ChapterListItem | null>(
  () => chapters.value.find((c) => c.id === selectedId.value) ?? null
)

// 章纲编辑：与选中章节双向同步
const editOutline = ref('')
watch(
  selectedChapter,
  (ch) => {
    editOutline.value = ch?.outline || ''
  },
  { immediate: true }
)

function selectChapter(ch: ChapterListItem) {
  selectedId.value = ch.id
}

// ===== 新建章节：使用 NModal 替代 window.prompt =====
const createChapterVisible = ref(false)
const createChapterTitle = ref('')

function handleCreateChapter() {
  if (creating.value) return
  createChapterTitle.value = '新章节'
  createChapterVisible.value = true
}

async function submitCreateChapter() {
  if (creating.value) return
  const title = createChapterTitle.value.trim() || '新章节'
  creating.value = true
  try {
    const created = await chapterStore.createChapter(novelId.value || '1', { title })
    selectedId.value = created.id
    createChapterVisible.value = false
    message.success('章节已创建')
  } catch (e) {
    console.error('Failed to create chapter:', e)
    message.error('创建失败，请重试')
  } finally {
    creating.value = false
  }
}

async function handleDeleteChapter(ch: ChapterListItem) {
  if (!ch.id) return
  if (!window.confirm(`确认删除章节「${ch.title}」？此操作不可撤销。`)) return
  try {
    await chapterStore.deleteChapter(ch.id)
    if (selectedId.value === ch.id) {
      selectedId.value = chapters.value[0]?.id ?? null
    }
    message.success('章节已删除')
  } catch (e) {
    console.error('Failed to delete chapter:', e)
    message.error('删除失败，请重试')
  }
}

async function handleSaveOutline() {
  if (!selectedChapter.value || outlineSaving.value) return
  outlineSaving.value = true
  try {
    await chapterStore.updateChapter(selectedChapter.value.id, { outline: editOutline.value })
    message.success('章纲已保存')
  } catch (e) {
    console.error('Failed to save outline:', e)
    message.error('保存失败，请重试')
  } finally {
    outlineSaving.value = false
  }
}

async function handleGenerateOutline() {
  if (!selectedChapter.value || generating.value) return
  generating.value = true
  try {
    const updated = await generateOutline(selectedChapter.value.id)
    await chapterStore.fetchChapters(novelId.value || '1', { force: true })
    selectedId.value = updated.id
  } catch (e) {
    console.error('Failed to generate outline:', e)
  } finally {
    generating.value = false
  }
}

onMounted(async () => {
  const nid = String(route.params.novelId || '1')
  await chapterStore.fetchChapters(nid)
  if (!selectedId.value && chapters.value.length > 0) {
    selectedId.value = chapters.value[0].id
  }
})
</script>

<style scoped>
.outline-page {
  display: flex;
  height: 100%;
}

.chapter-rail {
  width: 200px;
  border-right: 1px solid var(--xy-border-1);
  background: var(--xy-surface-1);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.rail-header {
  padding: 16px 12px;
  border-bottom: 1px solid var(--xy-border-1);
}

.rail-header h3 {
  font-size: 14px;
  font-weight: 600;
  color: var(--xy-text-1);
  margin: 0;
}

.chapter-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.chapter-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: var(--xy-radius-sm);
  cursor: pointer;
  font-size: 13px;
  color: var(--xy-text-2);
  transition: background-color 150ms ease;
}

.chapter-item:hover {
  background: var(--xy-surface-hover);
}

.chapter-item.active {
  background: var(--xy-surface-active);
  color: var(--xy-text-1);
  font-weight: 500;
}

.chapter-item .title {
  flex: 1;
  min-width: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.chapter-delete-btn {
  display: none;
  align-items: center;
  justify-content: center;
  width: 22px;
  height: 22px;
  border: none;
  background: transparent;
  color: var(--xy-text-3);
  border-radius: var(--xy-radius-xs);
  cursor: pointer;
  flex-shrink: 0;
  padding: 0;
  transition:
    color 150ms ease,
    background 150ms ease;
}

.chapter-item:hover .chapter-delete-btn {
  display: flex;
}

.chapter-delete-btn:hover {
  color: var(--xy-danger);
  background: var(--xy-danger-bg, rgba(220, 38, 38, 0.1));
}

.chapter-delete-icon {
  width: 14px;
  height: 14px;
}

.outline-textarea :deep(textarea) {
  font-size: 14px;
  line-height: 1.8;
  color: var(--xy-text-2);
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  flex-shrink: 0;
  background: var(--xy-text-4);
}

/* Sprint 1.5：对齐后端真实状态值（draft/planned/completed） */
.dot.completed {
  background: var(--xy-success);
}
.dot.draft {
  background: var(--xy-text-4);
}
.dot.planned {
  background: var(--xy-warning);
  box-shadow: 0 0 0 3px rgba(245, 158, 11, 0.18);
}

.rail-footer {
  padding: 12px;
  border-top: 1px solid var(--xy-border-1);
}

.outline-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: var(--xy-bg-canvas);
  min-width: 0;
}

.outline-toolbar {
  display: flex;
  justify-content: flex-end;
  padding: 12px 24px;
  border-bottom: 1px solid var(--xy-border-1);
  background: var(--xy-surface-1);
  flex-shrink: 0;
}

.view-toggle {
  display: flex;
  background: var(--xy-surface-2);
  border-radius: 6px;
  padding: 2px;
}

.toggle-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 6px 12px;
  border: none;
  background: transparent;
  color: var(--xy-text-3);
  font-size: 12px;
  cursor: pointer;
  border-radius: 4px;
  transition: all 0.2s;
}

.toggle-btn:hover {
  color: var(--xy-text-2);
}

.toggle-btn.active {
  background: var(--xy-brand-500);
  color: var(--xy-text-inverse);
}

.dag-container {
  flex: 1;
  overflow: hidden;
}

.outline-editor {
  flex: 1;
  padding: 32px 48px;
  overflow-y: auto;
}

.editor-content h2 {
  font-size: 20px;
  font-weight: 600;
  color: var(--xy-text-1);
  margin: 0 0 20px 0;
}

.outline-text {
  font-size: 14px;
  line-height: 1.8;
  color: var(--xy-text-2);
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  gap: 12px;
  color: var(--xy-text-3);
}

.empty-state p {
  margin: 0;
  font-size: 14px;
}

.outline-actions {
  padding: 16px 48px;
  border-top: 1px solid var(--xy-border-1);
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  background: var(--xy-surface-1);
}
</style>
