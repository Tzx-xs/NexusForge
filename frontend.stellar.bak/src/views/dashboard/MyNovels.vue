<template>
  <div class="my-novels-root">
    <div class="module-panel my-novels-panel">
    <div class="panel-inner">
      <!-- 氛围背景 -->
      <div class="ambient-bg">
        <div class="nebula nebula-1"/>
        <div class="nebula nebula-2"/>
        <div class="star-field"/>
      </div>

      <!-- Hero Header -->
      <header class="hero-header">
        <div class="hero-text">
          <div class="hero-eyebrow">我的创作</div>
          <h1 class="hero-title">在星渊深处，书写你的宇宙</h1>
          <p class="hero-desc">从一句话灵感开始，AI 将与你共同搭建世界观、人物与章节大纲。</p>
        </div>
        <div class="hero-tools">
          <div class="search-box">
            <Search class="search-icon"/>
            <input v-model="searchQuery" type="text" placeholder="搜索小说..." class="search-input"/>
          </div>
          <select v-model="filterStatus" class="filter-select">
            <option value="all">全部</option>
            <option value="ongoing">连载中</option>
            <option value="planning">计划中</option>
            <option value="completed">已完成</option>
          </select>
          <button class="btn-new-novel" @click="createNovel">
            <Plus class="icon-14"/>
            新建小说
          </button>
        </div>
      </header>

      <!-- 统计横条 -->
      <div class="stats-bar">
        <div class="stat-pill">
          <span class="stat-value">{{ novelStore.total }}</span>
          <span class="stat-label">作品总数</span>
        </div>
        <div class="stat-pill">
          <span class="stat-value">{{ totalWordCount }}</span>
          <span class="stat-label">累计字数</span>
        </div>
        <div class="stat-pill">
          <span class="stat-value">{{ inProgressCount }}</span>
          <span class="stat-label">连载中</span>
        </div>
      </div>

      <!-- 小说卡片网格 -->
      <section v-if="filteredNovels.length > 0" class="novels-section">
        <div class="novels-toolbar">
          <span class="novels-count">共 {{ filteredNovels.length }} 部作品</span>
          <div v-if="totalPages > 1" class="pagination">
            <button class="page-btn" :disabled="currentPage === 1" @click="goToPage(currentPage - 1)">
              <ChevronLeft class="icon-14"/>
            </button>
            <button
              v-for="page in totalPages"
              :key="page"
              class="page-number"
              :class="{ active: currentPage === page }"
              @click="goToPage(page)"
            >
              {{ page }}
            </button>
            <button class="page-btn" :disabled="currentPage === totalPages" @click="goToPage(currentPage + 1)">
              <ChevronRight class="icon-14"/>
            </button>
          </div>
        </div>

        <div class="novels-grid">
          <article
            v-for="(novel, index) in paginatedNovels"
            :key="novel.id"
            class="book-card"
            :style="{ '--stagger-delay': `${index * 60}ms` }"
            @contextmenu.prevent="showContextMenu($event, novel.id)"
          >
            <div class="cover-frame" @click="openNovel(novel.id)">
              <div class="card-cover" :style="{ background: getCover(novel) }">
                <span class="cover-tag">{{ novel.genre }}</span>
                <span class="cover-initial">{{ novel.title.charAt(0) }}</span>
                <div class="cover-glow"/>
                <Book class="cover-icon"/>
              </div>
              <div class="cover-actions">
                <button class="cover-action upload" title="上传封面" @click.stop="uploadCover(novel.id)">
                  <Photo class="icon-14"/>
                </button>
                <button class="cover-action delete" title="删除" @click.stop="deleteNovel(novel.id)">
                  <Trash class="icon-14"/>
                </button>
              </div>
            </div>
            <div class="card-body">
              <h3 class="card-title" @click="openNovel(novel.id)">{{ novel.title }}</h3>
              <div class="card-meta">
                <span class="meta-status" :class="novelStatus(novel)">{{ statusText(novelStatus(novel)) }}</span>
                <span v-if="novel.target_chapters > 0" class="meta-progress">{{ novel.current_chapter }}/{{ novel.target_chapters }} 章</span>
              </div>
              <div class="card-footer">
                <span class="word-count">{{ formatCount(novel.word_count) }} 字</span>
                <div class="progress-bar">
                  <div class="progress-fill" :style="{ width: `${Math.min(100, progressPercent(novel))}%` }"/>
                </div>
              </div>
            </div>
          </article>
        </div>
      </section>

      <!-- 空状态 -->
      <div v-else class="empty-state">
        <div class="empty-constellation">
          <div class="orbit orbit-1"/>
          <div class="orbit orbit-2"/>
          <div class="empty-star">
            <Book class="icon-40"/>
          </div>
        </div>
        <h3 class="empty-title">还没有小说</h3>
        <p class="empty-desc">创建第一部小说，开启你的星渊创作之旅</p>
        <button class="empty-btn" @click="createNovel">
          <Plus class="icon-14"/>
          新建小说
        </button>
      </div>
    </div>

    <!-- 隐藏封面上传输入 -->
    <input
      ref="coverInputRef"
      type="file"
      accept="image/*"
      class="cover-input"
      @change="onCoverSelected"
    />

    <!-- 右键菜单 -->
    <div
      v-if="contextMenu.show"
      class="context-menu xy-card-shimmer"
      :style="{ left: contextMenu.x + 'px', top: contextMenu.y + 'px' }"
    >
      <div class="context-menu-item" @click="ctxAction('edit')">
        <Pencil class="icon-14"/>
        编辑
      </div>
      <div class="context-menu-item" @click="ctxAction('export')">
        <Download class="icon-14"/>
        导出
      </div>
      <div class="context-menu-item danger" @click="ctxAction('delete')">
        <Trash class="icon-14"/>
        删除
      </div>
    </div>
  </div>

    <NovelDrawer
      v-model:visible="drawerVisible"
      :novel-id="selectedNovelId"
      @close="drawerVisible = false"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import { useNovelStore, type NovelWithStats } from '@/stores/novel'
import { Search, Book, Pencil, Download, Trash, Plus, Photo, ChevronLeft, ChevronRight } from '@vicons/tabler'
import NovelDrawer from '@/components/workspace/NovelDrawer.vue'

const message = useMessage()
const router = useRouter()
const novelStore = useNovelStore()

const drawerVisible = ref(false)
const selectedNovelId = ref('')

const searchQuery = ref('')
const filterStatus = ref('all')
const currentPage = ref(1)
const deletingIds = ref<Set<string>>(new Set())
const uploadingIds = ref<Set<string>>(new Set())
const coverInputRef = ref<HTMLInputElement>()
const pendingCoverNovelId = ref<string>('')

const itemsPerPage = computed(() => novelStore.pageSize)

function novelStatus(novel: NovelWithStats): 'ongoing' | 'planning' | 'completed' | 'generating' {
  if (novel.current_chapter === 0) return 'planning'
  if (novel.current_chapter >= novel.target_chapters && novel.target_chapters > 0) return 'completed'
  return 'ongoing'
}

function statusText(status: string): string {
  const map: Record<string, string> = {
    planning: '计划中',
    ongoing: '连载中',
    completed: '已完成',
    generating: '生成中'
  }
  return map[status] || status
}

function progressPercent(novel: NovelWithStats): number {
  if (!novel.target_chapters || novel.target_chapters <= 0) return 0
  return (novel.current_chapter / novel.target_chapters) * 100
}

function formatCount(n: number | string | undefined): string {
  const num = typeof n === 'number' ? n : Number(n || 0)
  if (num >= 10000) return (num / 10000).toFixed(1) + '万'
  if (num >= 1000) return (num / 1000).toFixed(1) + 'k'
  return String(num)
}

const totalWordCount = computed(() => {
  return formatCount(novelStore.novels.reduce((sum, n) => sum + Number(n.word_count || 0), 0))
})

const inProgressCount = computed(() => {
  return novelStore.novels.filter(n => novelStatus(n) === 'ongoing').length
})

const filteredNovels = computed(() => {
  let list = novelStore.novels
  if (filterStatus.value !== 'all') {
    list = list.filter(n => novelStatus(n) === filterStatus.value)
  }
  if (searchQuery.value.trim()) {
    const q = searchQuery.value.toLowerCase()
    list = list.filter(n => n.title.toLowerCase().includes(q))
  }
  return list
})

const paginatedNovels = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage.value
  const end = start + itemsPerPage.value
  return filteredNovels.value.slice(start, end)
})

const isFiltering = computed(() => filterStatus.value !== 'all' || !!searchQuery.value.trim())

const totalPages = computed(() => {
  if (isFiltering.value) {
    return Math.max(1, Math.ceil(filteredNovels.value.length / itemsPerPage.value))
  }
  return Math.max(1, Math.ceil(novelStore.total / itemsPerPage.value))
})

function goToPage(page: number) {
  if (page < 1 || page > totalPages.value) return
  currentPage.value = page
  novelStore.fetchNovels({ page })
}

function resetPage() {
  currentPage.value = 1
  novelStore.fetchNovels({ page: 1 })
}

function openNovel(id: string) {
  selectedNovelId.value = id
  drawerVisible.value = true
}

function createNovel() {
  router.replace({ query: { module: 'new-novel' } })
}

function exportNovel(id: string) {
  const novel = novelStore.novels.find(n => n.id === id)
  if (!novel) return
  const blob = new Blob([`# ${novel.title}\n\n${novel.premise || ''}`], { type: 'text/markdown;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${novel.title}.md`
  a.click()
  URL.revokeObjectURL(url)
  message.success('已开始导出')
}

async function deleteNovel(id: string) {
  if (!confirm('确定要删除这部小说吗？此操作不可撤销。')) return
  deletingIds.value.add(id)
  try {
    await novelStore.deleteNovel(id, { _silent: true })
    message.success('小说已删除')
    if (novelStore.novels.length === 0 && currentPage.value > 1) {
      currentPage.value -= 1
    }
    await novelStore.fetchNovels({ page: currentPage.value, force: true })
  } catch (e) {
    const errMsg = e instanceof Error ? e.message : '删除失败，请重试'
    message.error(errMsg)
  } finally {
    deletingIds.value.delete(id)
  }
}

function uploadCover(id: string) {
  pendingCoverNovelId.value = id
  coverInputRef.value?.click()
}

const MAX_COVER_SIZE = 2 * 1024 * 1024

async function onCoverSelected(e: Event) {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  const novelId = pendingCoverNovelId.value
  if (!file || !novelId) return

  if (file.size > MAX_COVER_SIZE) {
    message.error('封面图片过大，请选择 2MB 以内的图片')
    pendingCoverNovelId.value = ''
    if (target) target.value = ''
    return
  }

  uploadingIds.value.add(novelId)
  try {
    const dataUrl = await readFileAsDataURL(file)
    await novelStore.updateNovel(novelId, { cover_url: dataUrl })
    message.success('封面上传成功')
  } catch (err) {
    const errMsg = err instanceof Error ? err.message : '封面上传失败'
    message.error(errMsg)
  } finally {
    uploadingIds.value.delete(novelId)
    pendingCoverNovelId.value = ''
    if (target) target.value = ''
  }
}

function readFileAsDataURL(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(reader.result as string)
    reader.onerror = reject
    reader.readAsDataURL(file)
  })
}

const defaultCovers: Record<string, string> = {
  '玄幻': 'linear-gradient(135deg, #1a1633, #0c0b10)',
  '都市': 'linear-gradient(135deg, #2a1f0a, #0c0b10)',
  '科幻': 'linear-gradient(135deg, #0a1535, #0c0b10)',
  '武侠': 'linear-gradient(135deg, #15251a, #0c0b10)',
  '历史': 'linear-gradient(135deg, #251a15, #0c0b10)',
  '言情': 'linear-gradient(135deg, #2a1520, #0c0b10)',
  '悬疑': 'linear-gradient(135deg, #151825, #0c0b10)',
  '奇幻': 'linear-gradient(135deg, #1a1a33, #0c0b10)',
}

function getCover(novel: NovelWithStats): string {
  if (novel.cover_url) return novel.cover_url
  return defaultCovers[novel.genre] || 'linear-gradient(135deg, var(--xy-brand-200), var(--xy-bg-canvas))'
}

// Context Menu
const contextMenu = ref({ show: false, x: 0, y: 0, novelId: '' })

function showContextMenu(e: MouseEvent, novelId: string) {
  contextMenu.value = { show: true, x: e.clientX, y: e.clientY, novelId }
}

function ctxAction(action: string) {
  const id = contextMenu.value.novelId
  contextMenu.value.show = false
  if (action === 'edit') {
    openNovel(id)
  } else if (action === 'export') {
    exportNovel(id)
  } else if (action === 'delete') {
    deleteNovel(id)
  }
}

function hideContextMenuOnClick() {
  contextMenu.value.show = false
}

onMounted(() => {
  novelStore.fetchNovels({ page: currentPage.value })
  window.addEventListener('click', hideContextMenuOnClick)
})

onUnmounted(() => {
  window.removeEventListener('click', hideContextMenuOnClick)
})

watch([searchQuery, filterStatus], resetPage)
watch(() => novelStore.pageSize, resetPage)
</script>

<style scoped>
.my-novels-root {
  position: relative;
  min-height: 100%;
}

.my-novels-panel {
  position: relative;
  min-height: 100%;
  animation: xy-fade-in var(--xy-dur-md) var(--xy-ease-standard);
}

.panel-inner {
  position: relative;
  max-width: 1200px;
  margin: 0 auto;
  padding: 40px 32px 64px;
  z-index: 1;
}

/* 氛围背景 */
.ambient-bg {
  position: fixed;
  inset: 0;
  pointer-events: none;
  overflow: hidden;
  z-index: 0;
}

.nebula {
  position: absolute;
  border-radius: 50%;
  filter: blur(120px);
  opacity: 0.12;
}

.nebula-1 {
  width: 700px;
  height: 700px;
  top: -240px;
  right: -180px;
  background: radial-gradient(circle, var(--xy-brand-400) 0%, transparent 70%);
  animation: nebula-drift 20s ease-in-out infinite alternate;
}

.nebula-2 {
  width: 500px;
  height: 500px;
  bottom: -120px;
  left: -120px;
  background: radial-gradient(circle, var(--xy-accent-soft) 0%, transparent 70%);
  animation: nebula-drift 25s ease-in-out infinite alternate-reverse;
}

.star-field {
  position: absolute;
  inset: 0;
  background-image:
    radial-gradient(circle at 20% 30%, rgba(255,255,255,0.03) 0.5px, transparent 1px),
    radial-gradient(circle at 60% 70%, rgba(255,255,255,0.02) 0.5px, transparent 1px),
    radial-gradient(circle at 80% 20%, rgba(212,168,83,0.02) 0.5px, transparent 1px);
  background-size: 220px 220px, 180px 180px, 260px 260px;
  animation: star-twinkle 8s ease-in-out infinite;
}

@keyframes nebula-drift {
  from { transform: translate(0, 0) scale(1); }
  to { transform: translate(30px, 20px) scale(1.05); }
}

@keyframes star-twinkle {
  0%, 100% { opacity: 0.6; }
  50% { opacity: 1; }
}

/* Hero Header */
.hero-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 28px;
  margin-bottom: 28px;
  flex-wrap: wrap;
}

.hero-text {
  flex: 1;
  min-width: 320px;
}

.hero-eyebrow {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: var(--xy-brand-starlight);
  margin-bottom: 10px;
  opacity: 0.85;
}

.hero-title {
  font-family: var(--xy-font-display);
  font-size: clamp(28px, 4vw, 46px);
  font-weight: 500;
  color: var(--xy-text-1);
  letter-spacing: 0.02em;
  line-height: 1.15;
  margin: 0 0 12px;
}

.hero-desc {
  font-size: 15px;
  color: var(--xy-text-3);
  line-height: 1.6;
  margin: 0;
  max-width: 520px;
}

.hero-tools {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
  padding: 6px;
  background: var(--xy-surface-1);
  border: 1px solid var(--xy-border-1);
  border-radius: var(--xy-radius-lg, 10px);
}

.search-box {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 14px;
  border-radius: var(--xy-radius-md, 8px);
  border: 1px solid transparent;
  background: var(--xy-bg-page);
  transition: all var(--xy-dur-sm);
}

.search-box:focus-within {
  border-color: var(--xy-border-focus);
  background: var(--xy-surface-hover);
}

.search-icon {
  width: 15px;
  height: 15px;
  color: var(--xy-text-3);
  flex-shrink: 0;
}

.search-input {
  background: transparent;
  border: none;
  outline: none;
  color: var(--xy-text-2);
  font-size: 13px;
  width: 160px;
}

.search-input::placeholder {
  color: var(--xy-text-4);
}

.filter-select {
  padding: 8px 12px;
  border-radius: var(--xy-radius-md, 8px);
  border: 1px solid transparent;
  background: var(--xy-bg-page);
  color: var(--xy-text-2);
  font-size: 13px;
  cursor: pointer;
  outline: none;
}

.btn-new-novel {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 16px;
  border-radius: var(--xy-radius-md, 8px);
  border: none;
  background: linear-gradient(135deg, var(--xy-accent), #e8c46a);
  color: #1a1525;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--xy-dur-sm);
}

.btn-new-novel:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(212, 168, 83, 0.28);
}

/* Stats Bar */
.stats-bar {
  display: flex;
  gap: 14px;
  margin-bottom: 32px;
  flex-wrap: wrap;
}

.stat-pill {
  display: flex;
  align-items: baseline;
  gap: 8px;
  padding: 10px 18px;
  background: var(--xy-surface-1);
  border: 1px solid var(--xy-border-1);
  border-radius: var(--xy-radius-full, 9999px);
}

.stat-value {
  font-size: 18px;
  font-weight: 600;
  color: var(--xy-text-1);
  font-variant-numeric: tabular-nums;
}

.stat-label {
  font-size: 12px;
  color: var(--xy-text-3);
}

/* Novels Section */
.novels-section {
  animation: section-rise 0.6s var(--xy-ease-standard) forwards;
}

.novels-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  min-height: 28px;
}

.novels-count {
  font-size: 13px;
  color: var(--xy-text-3);
  letter-spacing: 0.02em;
}

.pagination {
  display: flex;
  align-items: center;
  gap: 6px;
}

.page-btn,
.page-number {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 28px;
  min-width: 28px;
  padding: 0 8px;
  border-radius: var(--xy-radius-sm, 5px);
  border: 1px solid var(--xy-border-1);
  background: var(--xy-surface-1);
  color: var(--xy-text-2);
  font-size: 12px;
  cursor: pointer;
  transition: all var(--xy-dur-sm);
}

.page-btn:hover:not(:disabled),
.page-number:hover:not(.active) {
  border-color: var(--xy-border-focus);
  color: var(--xy-text-1);
  background: var(--xy-surface-hover);
}

.page-btn:disabled {
  opacity: 0.35;
  cursor: not-allowed;
}

.page-number.active {
  background: linear-gradient(135deg, var(--xy-brand-500), var(--xy-brand-600));
  border-color: transparent;
  color: var(--xy-brand-starlight);
  font-weight: 600;
}

/* Grid */
.novels-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(170px, 1fr));
  gap: 24px 20px;
}

.book-card {
  --stagger-delay: 0ms;
  display: flex;
  flex-direction: column;
  gap: 12px;
  opacity: 0;
  transform: translateY(16px);
  animation: card-enter 0.5s var(--xy-ease-standard) var(--stagger-delay) forwards;
}

@keyframes card-enter {
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.book-card:hover .cover-actions {
  opacity: 1;
  transform: translateY(0);
}

.cover-frame {
  position: relative;
  padding: 2px;
  border-radius: 10px;
  background: linear-gradient(135deg, rgba(139, 126, 200, 0.45), rgba(212, 168, 83, 0.35));
  box-shadow: 0 4px 16px rgba(0, 0, 0, 0.35);
  cursor: pointer;
  overflow: hidden;
  transition: all var(--xy-dur-sm);
}

.cover-frame:hover {
  transform: translateY(-4px);
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.45), 0 0 0 1px rgba(212, 168, 83, 0.15);
}

.card-cover {
  position: relative;
  width: 100%;
  aspect-ratio: 3 / 4;
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background-size: cover;
  background-position: center;
}

.card-cover::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    radial-gradient(circle at 20% 30%, rgba(255, 255, 255, 0.05) 0%, transparent 45%),
    radial-gradient(circle at 80% 20%, rgba(212, 168, 83, 0.08) 0%, transparent 40%);
  pointer-events: none;
}

.cover-glow {
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at 50% 0%, rgba(212, 168, 83, 0.12) 0%, transparent 55%);
  opacity: 0;
  transition: opacity var(--xy-dur-sm);
  pointer-events: none;
}

.cover-frame:hover .cover-glow {
  opacity: 1;
}

.cover-tag {
  position: absolute;
  top: 8px;
  left: 8px;
  z-index: 2;
  padding: 3px 8px;
  border-radius: var(--xy-radius-full, 9999px);
  font-size: 10px;
  background: rgba(12, 11, 16, 0.72);
  color: var(--xy-text-1);
  border: 1px solid var(--xy-border-2);
  backdrop-filter: blur(6px);
}

.cover-initial {
  position: absolute;
  font-size: 48px;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.12);
  font-family: var(--xy-font-serif);
  user-select: none;
  line-height: 1;
  z-index: 1;
}

.cover-icon {
  position: relative;
  z-index: 1;
  width: 20px;
  height: 20px;
  color: var(--xy-text-1);
  opacity: 0.3;
}

.cover-actions {
  position: absolute;
  bottom: 8px;
  right: 8px;
  display: flex;
  gap: 6px;
  opacity: 0;
  transform: translateY(6px);
  transition: all var(--xy-dur-sm);
  z-index: 3;
}

.cover-action {
  width: 28px;
  height: 28px;
  border-radius: var(--xy-radius-md, 8px);
  border: 1px solid var(--xy-border-2);
  background: rgba(12, 11, 16, 0.75);
  color: var(--xy-text-1);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  backdrop-filter: blur(6px);
  transition: all var(--xy-dur-sm);
}

.cover-action:hover {
  background: var(--xy-surface-1);
  transform: scale(1.05);
}

.cover-action.delete:hover {
  color: var(--xy-danger);
  border-color: var(--xy-danger);
}

.card-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.card-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--xy-text-1);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin: 0;
  cursor: pointer;
  transition: color var(--xy-dur-sm);
}

.card-title:hover {
  color: var(--xy-brand-starlight);
}

.card-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.meta-status {
  font-size: 10px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: var(--xy-radius-full, 9999px);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.meta-status.planning {
  background: rgba(139, 126, 200, 0.15);
  color: var(--xy-brand-300);
}

.meta-status.ongoing {
  background: rgba(212, 168, 83, 0.15);
  color: var(--xy-accent);
}

.meta-status.completed {
  background: rgba(74, 222, 128, 0.12);
  color: var(--xy-success);
}

.meta-progress {
  font-size: 11px;
  color: var(--xy-text-4);
}

.card-footer {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.word-count {
  font-size: 11px;
  color: var(--xy-text-3);
}

.progress-bar {
  height: 3px;
  background: var(--xy-surface-2);
  border-radius: var(--xy-radius-full, 9999px);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: linear-gradient(90deg, var(--xy-brand-500), var(--xy-accent));
  border-radius: var(--xy-radius-full, 9999px);
  transition: width 0.6s var(--xy-ease-standard);
}

/* Empty State */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 24px;
  text-align: center;
  animation: section-rise 0.6s var(--xy-ease-standard) forwards;
}

.empty-constellation {
  position: relative;
  width: 120px;
  height: 120px;
  margin-bottom: 28px;
}

.orbit {
  position: absolute;
  border: 1px solid var(--xy-border-1);
  border-radius: 50%;
  inset: 0;
  opacity: 0.4;
}

.orbit-1 {
  animation: orbit-rotate 12s linear infinite;
}

.orbit-2 {
  inset: 18px;
  animation: orbit-rotate 18s linear infinite reverse;
}

.empty-star {
  position: absolute;
  inset: 32px;
  border-radius: 50%;
  background: var(--xy-surface-1);
  border: 1px solid var(--xy-border-2);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--xy-accent);
  box-shadow: 0 0 32px rgba(212, 168, 83, 0.12);
}

@keyframes orbit-rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.empty-title {
  font-family: var(--xy-font-display);
  font-size: 24px;
  font-weight: 500;
  color: var(--xy-text-1);
  margin-bottom: 8px;
}

.empty-desc {
  font-size: 14px;
  color: var(--xy-text-3);
  margin-bottom: 24px;
}

.empty-btn {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 12px 28px;
  border-radius: var(--xy-radius-md, 8px);
  border: none;
  background: linear-gradient(135deg, #c99a42, #d4a853 50%, #e0bd6e);
  color: #1a1525;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--xy-dur-sm);
}

.empty-btn:hover {
  filter: brightness(1.08);
  transform: translateY(-2px);
  box-shadow: 0 8px 24px rgba(212, 168, 83, 0.26);
}

/* Utilities */
.icon-14 {
  width: 14px;
  height: 14px;
}

.icon-40 {
  width: 40px;
  height: 40px;
}

.cover-input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
  pointer-events: none;
}

.context-menu {
  position: fixed;
  background: var(--xy-surface-1);
  border: 1px solid var(--xy-border-2);
  border-radius: var(--xy-radius-md, 8px);
  box-shadow: var(--xy-shadow-lg);
  padding: 6px;
  min-width: 160px;
  z-index: var(--xy-z-popover, 500);
  animation: xy-fade-in var(--xy-dur-sm) var(--xy-ease-standard);
}

.context-menu-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  font-size: 13px;
  color: var(--xy-text-2);
  border-radius: var(--xy-radius-sm, 5px);
  cursor: pointer;
  transition: all var(--xy-dur-sm);
}

.context-menu-item:hover {
  background: var(--xy-surface-hover);
  color: var(--xy-text-1);
}

.context-menu-item.danger {
  color: var(--xy-danger);
}

.context-menu-item.danger:hover {
  background: var(--xy-danger-bg);
}

@keyframes section-rise {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Responsive */
@media (max-width: 1024px) {
  .panel-inner {
    padding: 32px 24px 48px;
  }

  .novels-grid {
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
    gap: 20px 16px;
  }
}

@media (max-width: 768px) {
  .panel-inner {
    padding: 24px 16px 40px;
  }

  .hero-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 18px;
  }

  .hero-tools {
    width: 100%;
    flex-wrap: wrap;
  }

  .search-box {
    flex: 1;
  }

  .search-input {
    width: 100%;
  }

  .stats-bar {
    gap: 10px;
  }

  .stat-pill {
    padding: 8px 14px;
  }

  .stat-value {
    font-size: 16px;
  }

  .novels-grid {
    grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
    gap: 16px 12px;
  }

  .cover-initial {
    font-size: 34px;
  }
}

@media (max-width: 480px) {
  .novels-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .cover-initial {
    font-size: 28px;
  }

  .card-title {
    font-size: 13px;
  }
}
</style>