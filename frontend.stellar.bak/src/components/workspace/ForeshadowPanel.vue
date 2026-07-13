<template>
  <div class="foreshadow-panel">
    <div class="panel-header">
      <span class="panel-title">伏笔管理</span>
      <button class="add-btn" @click="showCreate = true">
        <Plus class="add-icon" />
        新建
      </button>
    </div>

    <div class="filter-bar">
      <div class="filter-tabs">
        <button
          v-for="f in filterOptions"
          :key="f.value"
          class="filter-tab"
          :class="{ active: activeFilter === f.value }"
          @click="activeFilter = f.value"
        >
          {{ f.label }}
          <span class="filter-count">{{ getFilterCount(f.value) }}</span>
        </button>
      </div>
    </div>

    <div class="foreshadow-list">
      <div v-if="loading" class="loading-state">加载中...</div>
      <div v-else-if="filteredForeshadows.length === 0" class="empty-state">
        <Bulb class="empty-icon" />
        <p>暂无伏笔</p>
      </div>
      <div
        v-for="item in filteredForeshadows"
        :key="item.id"
        class="foreshadow-card"
        :class="`priority-${item.priority.toLowerCase()}`"
      >
        <div class="card-header">
          <span class="card-title">{{ item.title }}</span>
          <span class="status-badge" :class="`status-${item.status}`">
            {{ statusMap[item.status] || item.status }}
          </span>
        </div>
        <p class="card-desc">{{ item.description || '暂无描述' }}</p>
        <div class="card-footer">
          <div class="card-meta">
            <span v-if="item.planted_chapter_index" class="meta-item">
              第{{ item.planted_chapter_index }}章埋设
            </span>
          </div>
          <div class="card-tags">
            <span v-for="tag in item.tags?.slice(0, 2) || []" :key="tag" class="tag">
              {{ tag }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <n-modal
      v-model:show="showCreate"
      preset="dialog"
      title="新建伏笔"
      positive-text="创建"
      negative-text="取消"
      @positive-click="handleCreate"
    >
      <div class="create-form">
        <div class="form-item">
          <label>标题</label>
          <n-input v-model:value="createForm.title" placeholder="请输入伏笔标题" />
        </div>
        <div class="form-item">
          <label>描述</label>
          <n-input
            v-model:value="createForm.description"
            type="textarea"
            :rows="3"
            placeholder="请输入伏笔描述"
          />
        </div>
        <div class="form-row">
          <div class="form-item">
            <label>优先级</label>
            <n-select v-model:value="createForm.priority" :options="priorityOptions" />
          </div>
          <div class="form-item">
            <label>状态</label>
            <n-select v-model:value="createForm.status" :options="statusOptions" />
          </div>
        </div>
      </div>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { Plus, Bulb } from '@vicons/tabler'
import { NModal, NInput, NSelect } from 'naive-ui'
import { getForeshadowList, createForeshadow, type Foreshadow } from '@/api/foreshadows'
import { useCurrentNovelId } from '@/composables/useCurrentNovelId'

const { novelId } = useCurrentNovelId()
const loading = ref(false)
const foreshadows = ref<Foreshadow[]>([])
const activeFilter = ref('all')
const showCreate = ref(false)

const filterOptions = [
  { value: 'all', label: '全部' },
  { value: 'planted', label: '已埋设' },
  { value: 'developing', label: '发展中' },
  { value: 'resolved', label: '已回收' },
]

const statusMap: Record<string, string> = {
  planted: '已埋设',
  developing: '发展中',
  resolved: '已回收',
  forgotten: '被遗忘',
}

const priorityOptions = [
  { label: 'P0 - 主线', value: 'P0' },
  { label: 'P1 - 重要', value: 'P1' },
  { label: 'P2 - 普通', value: 'P2' },
  { label: 'P3 - 彩蛋', value: 'P3' },
]

const statusOptions = [
  { label: '已埋设', value: 'planted' },
  { label: '发展中', value: 'developing' },
  { label: '已回收', value: 'resolved' },
]

const createForm = ref({
  title: '',
  description: '',
  priority: 'P2',
  status: 'planted',
})

const filteredForeshadows = computed(() => {
  if (activeFilter.value === 'all') return foreshadows.value
  return foreshadows.value.filter((f) => f.status === activeFilter.value)
})

function getFilterCount(filter: string) {
  if (filter === 'all') return foreshadows.value.length
  return foreshadows.value.filter((f) => f.status === filter).length
}

async function fetchForeshadows() {
  if (!novelId.value) return
  loading.value = true
  try {
    const res = await getForeshadowList(novelId.value)
    foreshadows.value = res
  } catch (e) {
    console.error('Failed to fetch foreshadows:', e)
  } finally {
    loading.value = false
  }
}

async function handleCreate() {
  if (!novelId.value || !createForm.value.title) return
  try {
    await createForeshadow(novelId.value, createForm.value)
    await fetchForeshadows()
    showCreate.value = false
    createForm.value = { title: '', description: '', priority: 'P2', status: 'planted' }
  } catch (e) {
    console.error('Failed to create foreshadow:', e)
  }
}

watch(novelId, fetchForeshadows)
onMounted(fetchForeshadows)
</script>

<style scoped>
.foreshadow-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.panel-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--xy-text-1);
}

.add-btn {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  border: 1px solid var(--xy-brand-400);
  background: transparent;
  color: var(--xy-brand-500);
  border-radius: 6px;
  font-size: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.add-btn:hover {
  background: var(--xy-brand-500);
  color: var(--xy-text-inverse);
}

.add-icon {
  width: 12px;
  height: 12px;
}

.filter-bar {
  margin-bottom: 12px;
}

.filter-tabs {
  display: flex;
  gap: 4px;
}

.filter-tab {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 6px 4px;
  border: none;
  background: var(--xy-surface-2);
  color: var(--xy-text-3);
  font-size: 11px;
  cursor: pointer;
  border-radius: 6px;
  transition: all 0.2s ease;
}

.filter-tab:hover {
  background: var(--xy-surface-hover);
  color: var(--xy-text-2);
}

.filter-tab.active {
  background: var(--xy-brand-500);
  color: var(--xy-text-inverse);
}

.filter-count {
  font-size: 10px;
  opacity: 0.7;
}

.foreshadow-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.loading-state,
.empty-state {
  text-align: center;
  padding: 30px 20px;
  color: var(--xy-text-4);
  font-size: 12px;
}

.empty-icon {
  width: 32px;
  height: 32px;
  margin-bottom: 8px;
  opacity: 0.3;
}

.foreshadow-card {
  padding: 10px 12px;
  background: var(--xy-surface-2);
  border-radius: 8px;
  border-left: 3px solid var(--xy-border-1);
  cursor: pointer;
  transition: all 0.2s ease;
}

.foreshadow-card:hover {
  background: var(--xy-surface-hover);
}

.foreshadow-card.priority-p0 {
  border-left-color: var(--xy-danger);
}

.foreshadow-card.priority-p1 {
  border-left-color: var(--xy-warning);
}

.foreshadow-card.priority-p2 {
  border-left-color: var(--xy-info);
}

.foreshadow-card.priority-p3 {
  border-left-color: var(--xy-text-4);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 8px;
  margin-bottom: 6px;
}

.card-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--xy-text-1);
  line-height: 1.4;
}

.status-badge {
  flex-shrink: 0;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 500;
}

.status-planted {
  background: color-mix(in srgb, var(--xy-info) 20%, transparent);
  color: var(--xy-info);
}

.status-developing {
  background: color-mix(in srgb, var(--xy-warning) 20%, transparent);
  color: var(--xy-warning);
}

.status-resolved {
  background: color-mix(in srgb, var(--xy-success) 20%, transparent);
  color: var(--xy-success);
}

.card-desc {
  font-size: 11px;
  color: var(--xy-text-3);
  line-height: 1.5;
  margin: 0 0 8px 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-meta {
  font-size: 10px;
  color: var(--xy-text-4);
}

.meta-item {
  margin-right: 8px;
}

.card-tags {
  display: flex;
  gap: 4px;
}

.tag {
  padding: 1px 6px;
  background: var(--xy-surface-1);
  color: var(--xy-text-3);
  border-radius: 3px;
  font-size: 10px;
}

.create-form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.form-item {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-item label {
  font-size: 12px;
  color: var(--xy-text-2);
  font-weight: 500;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
</style>
