<template>
  <div class="workspace-shell" :class="{ 'rail-collapsed': sidebarStore.collapsed }">
    <div class="workspace-grid">
      <!-- 顶部导航栏 -->
      <header class="topbar">
        <!-- 左侧：返回首页 + 侧边栏切换 + 小说标题 -->
        <div class="topbar-left">
          <div class="nav-controls">
            <button class="icon-btn nav-btn" aria-label="返回首页" @click="router.push('/')">
              <ArrowLeft class="icon" />
            </button>
            <button class="icon-btn nav-btn" aria-label="切换侧栏" @click="sidebarStore.toggle()">
              <Menu2 class="icon" />
            </button>
            <button
              v-if="isMobile"
              class="icon-btn nav-btn"
              aria-label="移动端菜单"
              @click="showMobileMenu = !showMobileMenu"
            >
              <Menu class="icon" />
            </button>
          </div>
          <div class="novel-title-group">
            <span class="novel-title">{{ novelTitle }}</span>
            <span class="writing-tag">写作</span>
          </div>
        </div>

        <!-- 中间区域 -->
        <div class="topbar-center">
          <!-- KPI 指标组 -->
          <div class="kpi-group">
            <div class="kpi-item">
              <Stack class="kpi-icon" />
              <span class="kpi-text">{{ chaptersLoading ? '—' : `${chapterCount} 章` }}</span>
            </div>
            <div class="kpi-divider"></div>
            <div class="kpi-item">
              <FileText class="kpi-icon kpi-icon-word" />
              <span class="kpi-text kpi-text-word">{{
                chaptersLoading ? '—' : formatWordCount(totalWords)
              }}</span>
            </div>
            <div class="kpi-divider"></div>
            <div class="kpi-item">
              <svg class="quality-ring" width="24" height="24" viewBox="0 0 24 24">
                <circle
                  cx="12"
                  cy="12"
                  r="10"
                  fill="none"
                  stroke="var(--xy-surface-2)"
                  stroke-width="2.5"
                />
                <circle
                  cx="12"
                  cy="12"
                  r="10"
                  fill="none"
                  stroke="var(--xy-brand-500)"
                  stroke-width="2.5"
                  :stroke-dasharray="qualityDashArray"
                  stroke-dashoffset="0"
                  stroke-linecap="round"
                  transform="rotate(-90 12 12)"
                />
              </svg>
              <span class="kpi-text kpi-text-quality">{{
                chaptersLoading ? '—' : avgScore ? `${avgScore}分` : '—'
              }}</span>
            </div>
            <div class="kpi-divider"></div>
            <div class="kpi-item">
              <span class="ai-pulse-dot" :class="{ 'ai-pulse-dot-offline': !networkOnline }"></span>
              <span class="kpi-text">{{ networkOnline ? 'AI 在线' : 'AI 离线' }}</span>
            </div>
          </div>
        </div>

        <!-- 右侧区域 -->
        <div class="topbar-right">
          <!-- 搜索 -->
          <button class="search-btn" @click="searchStore.open()">
            <Search class="search-icon" />
            <span class="search-placeholder">全局搜索</span>
            <span class="search-shortcut">⌘&nbsp;K</span>
          </button>

          <!-- 模式切换 -->
          <div class="mode-tabs">
            <button
              class="mode-tab"
              :class="{ 'mode-tab-active': currentMode === 'writing' }"
              @click="currentMode = 'writing'"
            >
              写作
            </button>
            <button
              class="mode-tab"
              :class="{ 'mode-tab-active': currentMode === 'autopilot' }"
              @click="toggleAutopilot"
            >
              {{ autopilotActive ? '自动驾驶中...' : '自动驾驶' }}
            </button>
          </div>

          <!-- 功能按钮组 -->
          <div class="action-buttons">
            <button class="icon-btn" aria-label="AI 建议" @click="handleBulbClick">
              <Bulb class="icon" />
            </button>
            <button class="icon-btn" aria-label="AI 对话" @click="agentPanelStore.open()">
              <MessageCircle class="icon" />
            </button>
            <button class="icon-btn" aria-label="历史记录" @click="handleHistoryClick">
              <Clock class="icon" />
            </button>
          </div>

          <!-- 用户区域 -->
          <div class="user-area">
            <ThemeSwitcher />
            <div class="user-avatar">{{ userInitial }}</div>
            <button class="icon-btn" aria-label="更多" @click="moreMenuVisible = !moreMenuVisible">
              <Dots class="icon" />
            </button>
            <div v-if="moreMenuVisible" ref="moreMenuRef" class="more-menu">
              <div class="more-menu-item" @click="handleExportCurrentChapter">导出当前章节</div>
              <div class="more-menu-item" @click="goToSettings">打开设置</div>
              <div class="more-menu-item" @click="showShortcutHint">快捷键面板</div>
            </div>
          </div>
        </div>
      </header>

      <!-- 左栏：章节导航 -->
      <aside class="left-panel" :class="{ 'mobile-open': showMobileMenu }">
        <slot name="chapterRail" />
      </aside>

      <!-- 中栏：工作区 -->
      <section class="center-panel">
        <slot />
      </section>

      <!-- 右栏：上下文面板 -->
      <aside class="right-panel">
        <slot name="contextPanel" />
      </aside>

      <!-- 底部状态栏 -->
      <footer class="statusbar">
        <div class="statusbar-left">
          <span class="status-text">{{ currentWordCount }} 字</span>
        </div>
        <div class="statusbar-center">
          <span class="status-text">{{ savedText }}</span>
          <span class="status-item">
            <span class="sync-dot"></span>
            <span class="status-text">实时同步</span>
          </span>
        </div>
        <div class="statusbar-right">
          <span class="status-text">Ln {{ editorStatusStore.cursorLine }}, Col {{ editorStatusStore.cursorCol }}</span>
          <span class="status-text">UTF-8</span>
        </div>
      </footer>
    </div>
    <XyDrawer :model-value="agentPanelStore.visible" placement="right" width="440px" title="AI 创作助手" @update:model-value="agentPanelStore.visible = $event">
      <AgentChatPanel :novel-id="novelId" />
    </XyDrawer>
    <AiSuggestPopover v-model:visible="showAiSuggest" />
    <GlobalSearchModal />
    <HistoryModal />
    <XyDialog
      v-model="shortcutDialogVisible"
      title="快捷键"
      confirm-text="知道了"
      @confirm="shortcutDialogVisible = false"
    >
      <div class="shortcut-list">
        <div class="shortcut-row">
          <span>全局搜索</span>
          <kbd>⌘&nbsp;K</kbd>
        </div>
        <div class="shortcut-row">
          <span>发送消息</span>
          <kbd>Enter</kbd>
        </div>
        <div class="shortcut-row">
          <span>换行</span>
          <kbd>Shift + Enter</kbd>
        </div>
        <div class="shortcut-row">
          <span>保存</span>
          <kbd>Ctrl + S</kbd>
        </div>
      </div>
    </XyDialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch, inject, type Ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import {
  Menu2,
  Search,
  Bulb,
  MessageCircle,
  Clock,
  Dots,
  Stack,
  FileText,
  ArrowLeft,
  Menu,
} from '@vicons/tabler'
import { useChapterStore } from '@/stores/chapter'
import { useNovelStore } from '@/stores/novel'
import { useSettingsStore } from '@/stores/settings'
import { useSaveStatusStore } from '@/stores/saveStatus'
import { useSidebarStore } from '@/stores/sidebar'
import { useEditorStatusStore } from '@/stores/editorStatus'
import { useSearchStore } from '@/stores/search'
import { useHistoryStore } from '@/stores/history'
import { useAgentPanelStore } from '@/stores/agentPanel'
import { useCurrentNovelId } from '@/composables/useCurrentNovelId'
import { toast } from '@/utils/toast'
import AgentChatPanel from './AgentChatPanel.vue'
import AiSuggestPopover from './AiSuggestPopover.vue'
import GlobalSearchModal from './GlobalSearchModal.vue'
import HistoryModal from './HistoryModal.vue'
import { XyDrawer, XyDialog } from '@/components/common'
import ThemeSwitcher from '@/components/common/ThemeSwitcher.vue'

const router = useRouter()
const route = useRoute()
const chapterStore = useChapterStore()
const novelStore = useNovelStore()
const settingsStore = useSettingsStore()
const saveStatusStore = useSaveStatusStore()
const sidebarStore = useSidebarStore()
const editorStatusStore = useEditorStatusStore()
const searchStore = useSearchStore()
const historyStore = useHistoryStore()
const { novelId } = useCurrentNovelId()

const agentPanelStore = useAgentPanelStore()
const showAiSuggest = ref(false)
const moreMenuVisible = ref(false)
const moreMenuRef = ref<HTMLElement | null>(null)
const isMobile = inject<Ref<boolean>>('isMobile') ?? ref(false)
const showMobileMenu = ref(false)

function handleClickOutside(e: MouseEvent) {
  if (moreMenuRef.value && !moreMenuRef.value.contains(e.target as Node)) {
    moreMenuVisible.value = false
  }
}

function handleBulbClick() {
  showAiSuggest.value = true
}

async function handleHistoryClick() {
  const chapterId =
    chapterStore.currentChapter?.id || (route.params.chapterId as string | undefined)
  await historyStore.open(chapterId, novelId.value)
}

function handleExportCurrentChapter() {
  moreMenuVisible.value = false
  const chapter = chapterStore.currentChapter
  if (!chapter || !chapter.content) {
    toast.warning('当前没有可导出的章节内容')
    return
  }
  const blob = new Blob(
    [`# ${chapter.title || '未命名章节'}\n\n${chapter.content}`],
    { type: 'text/markdown;charset=utf-8' }
  )
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${chapter.title || '章节'}.md`
  a.click()
  URL.revokeObjectURL(url)
  toast.success('章节导出成功')
}

function goToSettings() {
  moreMenuVisible.value = false
  router.push('/settings')
}

const shortcutDialogVisible = ref(false)

function showShortcutHint() {
  moreMenuVisible.value = false
  shortcutDialogVisible.value = true
}

const novelTitle = computed(() => {
  const novel = novelStore.novels.find((n) => n.id === novelId.value)
  return novel?.title || '未命名'
})

const currentWordCount = computed(() => {
  if (chapterStore.currentChapter) {
    return chapterStore.currentChapter.word_count || 0
  }
  const chapterId = route.params.chapterId as string | undefined
  if (chapterId) {
    const chapter = chapterStore.chapters.find((c) => c.id === chapterId)
    return chapter?.word_count || 0
  }
  return 0
})

const userInitial = computed(() => {
  const name = settingsStore.settings?.username
  return name ? name.charAt(0).toUpperCase() : '我'
})

const currentMode = ref<'writing' | 'autopilot'>('writing')
const autopilotActive = ref(false)

function toggleAutopilot() {
  if (currentMode.value === 'autopilot') {
    currentMode.value = 'writing'
    autopilotActive.value = false
  } else {
    currentMode.value = 'autopilot'
    autopilotActive.value = true
  }
}

const chaptersLoading = computed(() => chapterStore.loading)
const chapterCount = computed(() => chapterStore.chapters?.length || 0)
const totalWords = computed(
  () => chapterStore.chapters?.reduce((sum, c) => sum + (c.word_count || 0), 0) || 0
)
const avgScore = computed(() => {
  const list = chapterStore.chapters || []
  const valid = list.filter((c) => c.tension_score > 0)
  if (valid.length === 0) return 0
  return Math.round(valid.reduce((sum, c) => sum + c.tension_score, 0) / valid.length)
})
const qualityDashArray = computed(() => {
  const score = Math.min(100, Math.max(0, avgScore.value || 0))
  const circumference = 2 * Math.PI * 10
  const filled = (score / 100) * circumference
  return `${filled.toFixed(2)} ${circumference.toFixed(2)}`
})
const networkOnline = computed(() => (typeof navigator !== 'undefined' ? navigator.onLine : true))

// 自动保存状态文本（从 saveStatusStore 读取，由 useAutoSave 写入）
const savedText = computed(() => {
  if (saveStatusStore.isSaving) return '保存中…'
  const saved = saveStatusStore.lastSavedTime
  if (!saved) return '未保存'
  const diff = Date.now() - saved.getTime()
  if (diff < 60_000) return '已保存 · 刚刚'
  if (diff < 3_600_000) return `已保存 · ${Math.floor(diff / 60_000)}分钟前`
  return `已保存 · ${saved.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}`
})

function formatWordCount(n: number): string {
  if (!n) return '—'
  if (n >= 10000) return (n / 10000).toFixed(1) + '万'
  if (n >= 1000) return (n / 1000).toFixed(1) + 'k'
  return String(n)
}

// Sprint 5.3: 监听 query 参数 agentPanel,从 Home 页面跳转时自动打开 Agent 面板
watch(
  () => route.query.agentPanel,
  (val) => {
    if (val === 'open') agentPanelStore.open()
  },
  { immediate: true }
)

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
  if (novelStore.novels.length === 0) {
    novelStore.fetchNovels()
  }
  if (novelId.value && chapterStore.chapters.length === 0) {
    chapterStore.fetchChapters(novelId.value)
  }
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
.workspace-shell {
  height: 100vh;
  overflow: hidden;
  background: var(--xy-bg-page);
  color: var(--xy-text-1);
  font-family: var(--xy-font-sans);
  position: relative;
}

.workspace-grid {
  display: grid;
  height: 100vh;
  grid-template-rows: var(--xy-topbar-h) 1fr var(--xy-statusbar-h);
  grid-template-columns: 240px 1fr 320px;
  transition: grid-template-columns 0.2s var(--xy-ease-standard, ease);
}

/* 侧栏折叠态：左栏宽度变 0 */
.rail-collapsed .workspace-grid {
  grid-template-columns: 0 1fr 320px;
}

.workspace-shell.rail-collapsed .left-panel {
  width: 0;
  border-right: none;
  overflow: hidden;
  visibility: hidden;
}

/* ========== 顶部导航栏 ========== */
.topbar {
  grid-column: 1 / -1;
  grid-row: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--xy-space-4);
  background: var(--xy-topbar-gradient);
  border-bottom: var(--xy-border-w-1) solid var(--xy-border-1);
  z-index: var(--xy-z-sticky);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
}

.topbar-left {
  display: flex;
  align-items: center;
  gap: var(--xy-space-4);
}

.nav-controls {
  display: flex;
  align-items: center;
  gap: 2px;
}

.nav-btn {
  width: 32px;
  height: 32px;
}

.novel-title-group {
  display: flex;
  align-items: center;
  gap: var(--xy-space-2);
  padding-left: var(--xy-space-4);
  border-left: var(--xy-border-w-1) solid var(--xy-divider);
}

.novel-title {
  font-family: var(--xy-font-display);
  font-size: 14px;
  font-weight: 600;
  color: var(--xy-text-1);
  white-space: nowrap;
  letter-spacing: 0.01em;
}

.writing-tag {
  display: inline-flex;
  align-items: center;
  padding: 2px 9px;
  border-radius: var(--xy-radius-full);
  background: linear-gradient(135deg, var(--xy-brand-100), var(--xy-brand-50));
  color: var(--xy-brand-starlight);
  font-size: 11px;
  font-weight: 500;
  white-space: nowrap;
  border: 1px solid var(--xy-border-1);
  letter-spacing: 0.04em;
}

/* 中间区域 */
.topbar-center {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* KPI 指标组 */
.kpi-group {
  display: flex;
  align-items: center;
  gap: var(--xy-space-4);
  padding: var(--xy-space-1) var(--xy-space-4);
  background: var(--xy-surface-1);
  border-radius: var(--xy-radius-lg);
  border: var(--xy-border-w-1) solid var(--xy-border-1);
}

.kpi-divider {
  width: var(--xy-border-w-1);
  height: 24px;
  background: var(--xy-divider);
}

.kpi-item {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--xy-text-3);
  white-space: nowrap;
  transition: color var(--xy-dur-sm) var(--xy-ease-standard);
}

.kpi-item:hover {
  color: var(--xy-text-2);
}

.kpi-icon {
  width: 14px;
  height: 14px;
  color: var(--xy-text-4);
}

.kpi-icon-word {
  color: var(--xy-brand-500);
}

.kpi-text {
  color: var(--xy-text-3);
  font-weight: 500;
}

.kpi-text-word {
  color: var(--xy-brand-starlight);
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

.kpi-text-quality {
  font-weight: 600;
  color: var(--xy-text-2);
}

.quality-ring {
  flex-shrink: 0;
}

.ai-pulse-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  background: var(--xy-success);
  box-shadow: 0 0 8px rgba(74, 222, 128, 0.5);
  animation: xy-pulse-dot 2s ease-in-out infinite;
}

.ai-pulse-dot-offline {
  background: var(--xy-text-4);
  box-shadow: none;
  animation: none;
}

@keyframes xy-pulse-dot {
  0% {
    box-shadow: 0 0 0 0 rgba(74, 222, 128, 0.5);
  }
  70% {
    box-shadow: 0 0 0 8px transparent;
  }
  100% {
    box-shadow: 0 0 0 0 transparent;
  }
}

/* 右侧区域 */
.topbar-right {
  display: flex;
  align-items: center;
  gap: var(--xy-space-3);
  position: relative;
}

/* 搜索框 */
.search-btn {
  display: inline-flex;
  align-items: center;
  gap: var(--xy-space-2);
  padding: 0 var(--xy-space-3);
  height: 32px;
  border-radius: var(--xy-radius-md);
  border: var(--xy-border-w-1) solid var(--xy-border-1);
  background: var(--xy-surface-1);
  color: var(--xy-text-3);
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
  transition: all var(--xy-dur-sm) var(--xy-ease-standard);
}

.search-btn:hover {
  border-color: var(--xy-border-2);
  background: var(--xy-surface-hover);
  color: var(--xy-text-2);
}

.search-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.search-btn:disabled:hover {
  border-color: var(--xy-border-1);
  background: var(--xy-surface-1);
  color: var(--xy-text-3);
}

.search-icon {
  width: 13px;
  height: 13px;
}

.search-placeholder {
  color: var(--xy-text-4);
}

.search-shortcut {
  padding: 2px 6px;
  border-radius: var(--xy-radius-sm);
  background: var(--xy-surface-2);
  font-size: 10px;
  font-family: var(--xy-font-mono);
  color: var(--xy-text-4);
}

/* 模式切换 */
.mode-tabs {
  display: inline-flex;
  align-items: center;
  border-radius: var(--xy-radius-md);
  background: var(--xy-surface-1);
  border: var(--xy-border-w-1) solid var(--xy-border-1);
  overflow: hidden;
  padding: 2px;
}

.mode-tab {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 4px 14px;
  height: 26px;
  border: none;
  border-radius: var(--xy-radius-sm);
  background: transparent;
  color: var(--xy-text-3);
  font-size: 12px;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
  transition: all var(--xy-dur-sm) var(--xy-ease-standard);
  letter-spacing: 0.01em;
}

.mode-tab:hover {
  color: var(--xy-text-2);
}

.mode-tab-active {
  background: linear-gradient(135deg, var(--xy-brand-500), var(--xy-brand-600));
  color: var(--xy-brand-starlight);
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(124, 108, 191, 0.3);
}

/* 功能按钮组 */
.action-buttons {
  display: flex;
  align-items: center;
  gap: 2px;
  padding: var(--xy-space-1);
  background: var(--xy-surface-1);
  border-radius: var(--xy-radius-md);
  border: var(--xy-border-w-1) solid var(--xy-border-1);
}

/* 用户区域 */
.user-area {
  display: flex;
  align-items: center;
  gap: 2px;
  padding-left: var(--xy-space-3);
  border-left: var(--xy-border-w-1) solid var(--xy-divider);
  position: relative;
}

.user-avatar {
  width: 30px;
  height: 30px;
  border-radius: var(--xy-radius-full);
  background: linear-gradient(135deg, var(--xy-brand-500), var(--xy-brand-700));
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--xy-brand-starlight);
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  margin: 0 4px;
  box-shadow: 0 2px 8px rgba(124, 108, 191, 0.3);
  transition: all var(--xy-dur-sm) var(--xy-ease-standard);
}

.user-avatar:hover {
  transform: scale(1.05);
  box-shadow: 0 4px 12px rgba(124, 108, 191, 0.4);
}

.more-menu {
  position: absolute;
  top: calc(100% + 4px);
  right: 0;
  min-width: 160px;
  background: var(--xy-surface-1);
  border: 1px solid var(--xy-border-1);
  border-radius: 8px;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
  padding: 4px 0;
  z-index: 100;
  animation: xy-fade-in var(--xy-dur-xs) var(--xy-ease-standard);
}

.more-menu-item {
  padding: 8px 14px;
  font-size: 13px;
  color: var(--xy-text-2);
  cursor: pointer;
  transition: background 0.15s ease;
}

.more-menu-item:hover {
  background: var(--xy-surface-hover);
  color: var(--xy-text-1);
}

.icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: var(--xy-radius-md);
  border: none;
  background: transparent;
  color: var(--xy-text-3);
  cursor: pointer;
  transition: all var(--xy-dur-sm) var(--xy-ease-standard);
}

.icon-btn:hover {
  color: var(--xy-brand-starlight);
  background: var(--xy-surface-hover);
}

.icon-btn:active {
  background: var(--xy-surface-active);
  transform: scale(0.92);
}

.icon-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.icon-btn:disabled:hover {
  color: var(--xy-text-3);
  background: transparent;
}

.icon {
  width: 16px;
  height: 16px;
}

/* ========== 左栏 ========== */
.left-panel {
  grid-column: 1;
  grid-row: 2;
  display: flex;
  flex-direction: column;
  background: var(--xy-surface-1);
  border-right: var(--xy-border-w-1) solid var(--xy-split-border);
  overflow: hidden;
}

/* ========== 中栏 ========== */
.center-panel {
  grid-column: 2;
  grid-row: 2;
  display: flex;
  flex-direction: column;
  background: var(--xy-bg-canvas);
  overflow: hidden;
  position: relative;
}

/* ========== 右栏 ========== */
.right-panel {
  grid-column: 3;
  grid-row: 2;
  display: flex;
  flex-direction: column;
  background: var(--xy-surface-1);
  border-left: var(--xy-border-w-1) solid var(--xy-split-border);
  overflow: hidden;
}

/* ========== 底部状态栏 ========== */
.statusbar {
  grid-column: 1 / -1;
  grid-row: 3;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--xy-space-4);
  background: var(--xy-surface-1);
  border-top: var(--xy-border-w-1) solid var(--xy-split-border);
  font-size: 11px;
  color: var(--xy-text-4);
  font-family: var(--xy-font-mono);
  backdrop-filter: blur(8px);
  -webkit-backdrop-filter: blur(8px);
}

.statusbar-left,
.statusbar-center,
.statusbar-right {
  display: flex;
  align-items: center;
  gap: var(--xy-space-4);
}

.statusbar-center {
  flex: 1;
  justify-content: center;
}

.status-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.status-text {
  font-variant-numeric: tabular-nums;
  color: var(--xy-text-4);
  font-weight: 500;
}

.sync-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--xy-success);
  box-shadow: 0 0 6px rgba(74, 222, 128, 0.4);
}

@media (prefers-reduced-motion: reduce) {
  .ai-pulse-dot,
  .icon-btn,
  .search-btn,
  .user-avatar {
    transition-duration: 0.01ms !important;
    animation-duration: 0.01ms !important;
  }
}
</style>
