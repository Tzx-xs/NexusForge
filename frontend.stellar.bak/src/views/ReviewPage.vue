<template>
  <div class="review-page">
    <header class="topbar">
      <div class="topbar-left">
        <button class="back-home-btn" aria-label="返回首页" @click="router.push('/')">
          <ArrowLeft class="back-icon" />
          <span>返回首页</span>
        </button>
        <Book2 class="brand-icon" />
        <span class="brand-text">星渊笔</span>
        <span class="divider"></span>
        <span class="novel-title">{{ novelTitle }}</span>
      </div>
      <div class="topbar-right">
        <span class="review-badge">
          <AlertTriangle class="badge-icon" />
          审查
        </span>
        <div class="nav-icons">
          <button class="nav-icon-btn" title="写作模式" @click="goToWriting">
            <Pencil class="nav-icon" />
          </button>
          <button class="nav-icon-btn" title="设置" @click="goToSettings">
            <Settings class="nav-icon" />
          </button>
        </div>
        <span class="divider"></span>
        <div class="word-count">
          <span class="count-text">{{ wordCountText }}</span>
          <span class="status-dot"></span>
        </div>
      </div>
    </header>

    <div class="main-content">
      <aside class="left-panel">
        <div class="panel-header">
          <span class="panel-title">审查结果</span>
          <span class="result-count">{{ filteredIssues.length }}</span>
        </div>

        <div class="category-tabs">
          <button
            v-for="tab in categories"
            :key="tab.value"
            :class="['tab-btn', { active: activeCategory === tab.value }]"
            @click="activeCategory = tab.value"
          >
            <component :is="tab.icon" class="tab-icon" />
            <span>{{ tab.label }}</span>
          </button>
        </div>

        <div class="issues-list">
          <div v-if="reviewLoading" class="issues-loading">
            <Refresh class="loading-spin" />
            <span>审查中…</span>
          </div>
          <div v-else-if="filteredIssues.length === 0" class="issues-empty">
            <span>暂无审查结果</span>
          </div>
          <div
            v-for="issue in filteredIssues"
            :key="issue.id"
            :class="['issue-card', { active: selectedIssue?.id === issue.id }]"
            @click="selectedIssue = issue"
          >
            <div class="issue-header">
              <span :class="['issue-type', `type-${issue.type}`]">
                {{ issue.typeLabel }}
              </span>
              <span :class="['severity', `severity-${issue.severity}`]">
                {{ issue.severityLabel }}
              </span>
            </div>
            <h4 class="issue-title">{{ issue.title }}</h4>
            <div class="issue-location">
              <FileText class="location-icon" />
              <span>{{ issue.location }}</span>
            </div>
          </div>
        </div>

        <div class="panel-footer">
          <button class="btn-start-review" :disabled="reviewLoading" @click="startReview">
            <Refresh class="btn-icon" :class="{ spinning: reviewLoading }" />
            {{ reviewLoading ? '审查中…' : '开始审查' }}
          </button>
        </div>
      </aside>

      <section class="right-panel">
        <div v-if="selectedIssue" class="detail-header">
          <h3 class="detail-title">问题详情</h3>
          <div class="detail-meta">
            <span :class="['issue-type', `type-${selectedIssue.type}`]">
              {{ selectedIssue.typeLabel }}
            </span>
            <span :class="['severity', `severity-${selectedIssue.severity}`]">
              {{ selectedIssue.severityLabel }}
            </span>
          </div>
        </div>

        <div v-else class="detail-empty">
          <AlertTriangle class="empty-icon" />
          <p class="empty-text">选择一个问题查看详情</p>
        </div>

        <div v-if="selectedIssue" class="detail-content">
          <div class="detail-section">
            <h4 class="section-title">问题描述</h4>
            <p class="description-text">{{ selectedIssue.description }}</p>
          </div>

          <div class="detail-section">
            <h4 class="section-title">原文片段</h4>
            <div class="original-text">
              <p>
                {{ selectedIssue.beforeText }}
                <mark class="highlight-error">{{ selectedIssue.highlightText }}</mark>
                {{ selectedIssue.afterText }}
              </p>
            </div>
          </div>

          <div class="detail-section">
            <h4 class="section-title">
              <Stars class="section-icon" />
              AI 修改建议
            </h4>
            <div class="suggestion-text">
              <p>
                {{ selectedIssue.suggestionBefore }}
                <span class="highlight-fix">{{ selectedIssue.suggestionFix }}</span>
                {{ selectedIssue.suggestionAfter }}
              </p>
            </div>
          </div>

          <div class="action-buttons">
            <button class="btn-adopt" @click="adoptIssue">
              <Check class="btn-icon" />
              采纳修改
            </button>
            <button class="btn-ignore" @click="ignoreIssue">
              <X class="btn-icon" />
              忽略
            </button>
            <button class="btn-manual" @click="manualEdit">
              <Pencil class="btn-icon" />
              手动修改
            </button>
          </div>
        </div>
      </section>
    </div>

    <footer class="statusbar">
      <div class="status-left">
        <div class="status-item">
          <span class="pulse-dot"></span>
          <span class="status-text">审查就绪</span>
        </div>
        <span class="status-divider">|</span>
        <span class="status-text">共 {{ totalIssuesText }} 个问题</span>
        <span class="status-divider">|</span>
        <span class="status-text">{{ chapterProgressText }}</span>
      </div>
      <div class="status-right">
        <span class="ai-dot"></span>
        <span class="status-text">AI 在线</span>
      </div>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getReview, reviewChapter } from '@/api/review'
import type { ReviewResult } from '@/api/review'
import { updateChapter } from '@/api/chapters'
import { useNovelStore } from '@/stores/novel'
import { useChapterStore } from '@/stores/chapter'
import { useCurrentNovelId } from '@/composables/useCurrentNovelId'
import { toast } from '@/utils/toast'
import {
  AlertTriangle,
  User,
  Book,
  FileText,
  Check,
  X,
  Pencil,
  Settings,
  Refresh,
  LayoutList,
  Book2,
  Stars,
  ArrowLeft,
} from '@vicons/tabler'

interface ReviewIssue {
  id: number
  type: 'logic' | 'character' | 'setting' | 'style'
  typeLabel: string
  title: string
  location: string
  severity: 'high' | 'medium' | 'low'
  severityLabel: string
  description: string
  beforeText: string
  highlightText: string
  afterText: string
  suggestionBefore: string
  suggestionFix: string
  suggestionAfter: string
}

const route = useRoute()
const router = useRouter()
const novelStore = useNovelStore()
const chapterStore = useChapterStore()
const { novelId } = useCurrentNovelId()

const activeCategory = ref<string>('all')
const selectedIssue = ref<ReviewIssue | null>(null)

const categories = [
  { value: 'all', label: '全部', icon: LayoutList },
  { value: 'logic', label: '逻辑', icon: AlertTriangle },
  { value: 'character', label: '人物', icon: User },
  { value: 'setting', label: '设定', icon: Book },
  { value: 'style', label: '文笔', icon: FileText },
]

const apiReviewResult = ref<ReviewResult | null>(null)
const reviewLoading = ref(false)

// 已忽略的问题 id 集合，本地标记避免重复弹出
const ignoredIssueIds = ref<Set<number>>(new Set())

const novelTitle = computed(() => {
  const novel = novelStore.novels.find((n) => n.id === novelId.value)
  return novel?.title || '未命名小说'
})

const typeLabelMap: Record<string, string> = {
  logic: '逻辑错误',
  character: '人物OOC',
  setting: '设定冲突',
  style: '文笔建议',
}

const severityLabelMap: Record<string, string> = {
  high: '高',
  medium: '中',
  low: '低',
}

function normalizeType(type: string): ReviewIssue['type'] {
  if (type === 'logic' || type === 'character' || type === 'setting' || type === 'style') {
    return type
  }
  return 'style'
}

function normalizeSeverity(severity: string): ReviewIssue['severity'] {
  if (severity === 'high' || severity === 'medium' || severity === 'low') {
    return severity
  }
  return 'low'
}

const issues = computed<ReviewIssue[]>(() => {
  const details = apiReviewResult.value?.review_details
  if (!details || details.length === 0) {
    return []
  }
  return details.map((detail, index) => {
    const type = normalizeType(detail.type)
    const severity = normalizeSeverity(detail.severity)
    return {
      id: index + 1,
      type,
      typeLabel: typeLabelMap[type] || detail.type,
      title: typeLabelMap[type] || detail.type,
      location: detail.location || '未知位置',
      severity,
      severityLabel: severityLabelMap[severity] || severity,
      description: detail.description || '',
      beforeText: '',
      highlightText: detail.description || '',
      afterText: '',
      suggestionBefore: '',
      suggestionFix: detail.suggestion || '',
      suggestionAfter: '',
    }
  })
})

const filteredIssues = computed(() => {
  const base =
    activeCategory.value === 'all'
      ? issues.value
      : issues.value.filter((issue) => issue.type === activeCategory.value)
  return base.filter((issue) => !ignoredIssueIds.value.has(issue.id))
})

const currentChapterWordCount = computed(() => chapterStore.currentChapter?.word_count || 0)
const currentChapterNumber = computed(() => chapterStore.currentChapter?.number || 0)
const targetChapters = computed(() => {
  const novel = novelStore.novels.find((n) => n.id === novelId.value)
  return novel?.target_chapters || 0
})
const totalIssues = computed(() => apiReviewResult.value?.review_details?.length || 0)

const wordCountText = computed(() => {
  const wc = currentChapterWordCount.value
  if (!wc) return reviewLoading.value ? '—' : '0 字'
  return `${wc.toLocaleString('zh-CN')} 字`
})

const totalIssuesText = computed(() => {
  if (reviewLoading.value && totalIssues.value === 0) return '—'
  return String(totalIssues.value)
})

const chapterProgressText = computed(() => {
  const num = currentChapterNumber.value
  const target = targetChapters.value
  if (!num && !target) return '—'
  return `第${num || '—'}章 / ${target || '—'}章`
})

async function startReview() {
  const chapterId = chapterStore.currentChapter?.id
  if (!chapterId) {
    toast.error('未选中章节，无法审查')
    return
  }
  reviewLoading.value = true
  try {
    const result = await reviewChapter(chapterId)
    apiReviewResult.value = result
    ignoredIssueIds.value = new Set()
    selectedIssue.value = null
    toast.success(`审查完成，共发现 ${result.review_details?.length || 0} 个问题`)
  } catch (e: unknown) {
    const err = e as { message?: string }
    toast.error(err?.message || '审查失败')
  } finally {
    reviewLoading.value = false
  }
}

async function adoptIssue() {
  if (!selectedIssue.value) return
  const issue = selectedIssue.value
  const chapterId = chapterStore.currentChapter?.id
  const currentContent = chapterStore.currentChapter?.content

  if (!chapterId) {
    toast.warning('未识别到章节，无法采纳')
    return
  }

  if (!issue.suggestionFix) {
    toast.info('该问题没有自动修改建议')
    ignoredIssueIds.value.add(issue.id)
    selectedIssue.value = null
    return
  }

  // 尝试在正文中定位问题描述并替换为建议文本
  if (currentContent && issue.highlightText && currentContent.includes(issue.highlightText)) {
    try {
      const newContent = currentContent.replace(issue.highlightText, issue.suggestionFix)
      await updateChapter(chapterId, { content: newContent })
      if (chapterStore.currentChapter) {
        chapterStore.currentChapter.content = newContent
      }
      toast.success('已应用修改建议')
      ignoredIssueIds.value.add(issue.id)
      selectedIssue.value = null
      return
    } catch (e) {
      toast.error('应用修改失败，请手动修改')
      return
    }
  }

  // 无法自动定位原文时，提示用户手动修改
  toast.info('无法在正文中自动定位该问题，建议手动修改')
}

function ignoreIssue() {
  if (!selectedIssue.value) return
  ignoredIssueIds.value.add(selectedIssue.value.id)
  selectedIssue.value = null
  toast.info('已忽略该问题')
}

function manualEdit() {
  if (!selectedIssue.value) return
  const chapterId = chapterStore.currentChapter?.id
  const novelIdValue = novelId.value
  if (!chapterId || !novelIdValue) {
    toast.warning('未识别到章节，无法跳转')
    return
  }
  router.push(`/workspace/${novelIdValue}/writing?chapter=${chapterId}`)
}

function goToWriting() {
  const novelIdValue = novelId.value
  if (!novelIdValue) {
    toast.warning('未识别到小说')
    return
  }
  router.push(`/workspace/${novelIdValue}/writing`)
}

function goToSettings() {
  router.push('/settings')
}

onMounted(async () => {
  if (novelStore.novels.length === 0) {
    await novelStore.fetchNovels()
  }
  if (chapterStore.chapters.length === 0 && novelId.value) {
    await chapterStore.fetchChapters(novelId.value)
  }

  let chapterId = String(route.params.chapterId || '')
  if (!chapterId && chapterStore.chapters.length > 0) {
    chapterId = chapterStore.chapters[0].id
  }
  if (!chapterId) {
    // 无可用章节时不硬编码 '1'，避免请求不存在的资源（审查报告 5.5）
    return
  }

  if (!chapterStore.currentChapter || chapterStore.currentChapter.id !== chapterId) {
    await chapterStore.fetchChapter(chapterId)
  }

  reviewLoading.value = true
  try {
    const result = await getReview(chapterId)
    if (result) {
      apiReviewResult.value = result
    }
  } catch (e) {
    console.error('Failed to fetch review:', e)
  } finally {
    reviewLoading.value = false
  }
})
</script>

<style scoped>
.review-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: var(--xy-bg-page);
  overflow: hidden;
}

.topbar {
  height: var(--xy-topbar-h);
  background: var(--xy-topbar-gradient);
  border-bottom: 1px solid var(--xy-border-1);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  flex-shrink: 0;
  position: relative;
  z-index: var(--xy-z-nav-fixed);
}

.topbar-left,
.topbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.back-home-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 30px;
  padding: 0 12px;
  border-radius: var(--xy-radius-sm);
  border: 1px solid var(--xy-border-1);
  background: var(--xy-surface-1);
  color: var(--xy-text-2);
  font-size: var(--xy-fs-sm);
  font-family: var(--xy-font-sans);
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
  transition: all var(--xy-dur-sm) var(--xy-ease-standard);
}

.back-home-btn:hover {
  border-color: var(--xy-border-2);
  background: var(--xy-surface-hover);
  color: var(--xy-brand-starlight);
}

.back-icon {
  width: 14px;
  height: 14px;
}

.brand-icon {
  width: 16px;
  height: 16px;
  color: var(--xy-brand-500);
}

.brand-text {
  font-family: var(--xy-font-serif);
  font-size: var(--xy-fs-md);
  color: var(--xy-text-1);
  font-weight: 600;
  white-space: nowrap;
}

.divider {
  width: 1px;
  height: 16px;
  background: var(--xy-border-1);
}

.novel-title {
  font-size: var(--xy-fs-sm);
  color: var(--xy-text-2);
  font-weight: 500;
  white-space: nowrap;
}

.review-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 10px;
  border-radius: var(--xy-radius-full);
  background: var(--xy-brand-100);
  color: var(--xy-brand-starlight);
  border: 1px solid var(--xy-border-2);
  font-size: var(--xy-fs-xs);
  font-weight: 500;
  white-space: nowrap;
}

.badge-icon {
  width: 12px;
  height: 12px;
}

.nav-icons {
  display: flex;
  align-items: center;
  gap: 2px;
}

.nav-icon-btn {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--xy-radius-sm);
  background: transparent;
  border: none;
  color: var(--xy-text-3);
  cursor: pointer;
  transition:
    background-color var(--xy-dur-sm) var(--xy-ease-standard),
    color var(--xy-dur-sm) var(--xy-ease-standard);
}

.nav-icon-btn:hover {
  color: var(--xy-text-1);
  background: var(--xy-surface-hover);
}

.nav-icon {
  width: 14px;
  height: 14px;
}

.word-count {
  display: flex;
  align-items: center;
  gap: 8px;
}

.count-text {
  font-size: var(--xy-fs-xs);
  color: var(--xy-text-3);
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--xy-brand-500);
  box-shadow: 0 0 6px rgba(124, 108, 191, 0.5);
  display: inline-block;
}

.main-content {
  flex: 1;
  display: flex;
  overflow: hidden;
}

.left-panel {
  width: 320px;
  min-width: 280px;
  max-width: 360px;
  border-right: 1px solid var(--xy-border-1);
  background: var(--xy-bg-canvas);
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-header {
  height: var(--xy-panel-header-h);
  border-bottom: 1px solid var(--xy-border-1);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  flex-shrink: 0;
}

.panel-title {
  font-size: var(--xy-fs-sm);
  font-weight: 600;
  color: var(--xy-text-1);
  white-space: nowrap;
}

.result-count {
  font-size: var(--xy-fs-xs);
  color: var(--xy-text-3);
  background: var(--xy-surface-2);
  padding: 2px 8px;
  border-radius: var(--xy-radius-full);
}

.category-tabs {
  display: flex;
  padding: 8px;
  gap: 4px;
  border-bottom: 1px solid var(--xy-border-1);
  flex-shrink: 0;
}

.tab-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 6px 8px;
  border-radius: var(--xy-radius-sm);
  background: transparent;
  border: none;
  color: var(--xy-text-3);
  font-size: var(--xy-fs-xs);
  font-weight: 500;
  cursor: pointer;
  transition:
    background-color var(--xy-dur-sm) var(--xy-ease-standard),
    color var(--xy-dur-sm) var(--xy-ease-standard);
  white-space: nowrap;
}

.tab-btn:hover {
  background: var(--xy-surface-hover);
  color: var(--xy-text-2);
}

.tab-btn.active {
  background: var(--xy-brand-200);
  color: var(--xy-brand-starlight);
}

.tab-icon {
  width: 12px;
  height: 12px;
}

.issues-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  scrollbar-gutter: stable;
}

.issue-card {
  padding: 10px 12px;
  border-radius: var(--xy-radius-md);
  background: var(--xy-surface-2);
  border: 1px solid transparent;
  cursor: pointer;
  transition:
    border-color var(--xy-dur-sm) var(--xy-ease-standard),
    background-color var(--xy-dur-sm) var(--xy-ease-standard);
}

.issue-card:hover {
  border-color: var(--xy-border-2);
}

.issue-card.active {
  border-color: var(--xy-brand-400);
  background: var(--xy-surface-hover);
}

.issue-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.issue-type {
  font-size: 10px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: var(--xy-radius-xs);
}

.type-logic {
  background: var(--xy-danger-bg);
  color: var(--xy-danger);
}

.type-character {
  background: var(--xy-warning-bg);
  color: var(--xy-warning);
}

.type-setting {
  background: rgba(251, 191, 36, 0.1);
  color: var(--xy-warning);
}

.type-style {
  background: var(--xy-info-bg);
  color: var(--xy-info);
}

.severity {
  font-size: 10px;
  font-weight: 500;
  padding: 1px 6px;
  border-radius: var(--xy-radius-xs);
}

.severity-high {
  background: rgba(248, 113, 113, 0.15);
  color: var(--xy-danger);
}

.severity-medium {
  background: rgba(251, 191, 36, 0.15);
  color: var(--xy-warning);
}

.severity-low {
  background: rgba(129, 140, 248, 0.15);
  color: var(--xy-info);
}

.issue-title {
  font-size: var(--xy-fs-sm);
  font-weight: 500;
  color: var(--xy-text-1);
  margin: 0 0 6px 0;
  line-height: 1.4;
}

.issue-location {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: var(--xy-fs-xs);
  color: var(--xy-text-4);
}

.location-icon {
  width: 10px;
  height: 10px;
  flex-shrink: 0;
}

.panel-footer {
  padding: 12px;
  border-top: 1px solid var(--xy-border-1);
  flex-shrink: 0;
}

.btn-start-review {
  width: 100%;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border-radius: var(--xy-radius-md);
  background: var(--xy-brand-500);
  color: var(--xy-text-inverse);
  font-size: var(--xy-fs-sm);
  font-weight: 600;
  font-family: var(--xy-font-sans);
  border: none;
  cursor: pointer;
  transition:
    filter var(--xy-dur-sm) var(--xy-ease-standard),
    transform var(--xy-dur-xs) var(--xy-ease-standard);
}

.btn-start-review:hover {
  filter: brightness(1.1);
  transform: translateY(-1px);
}

.btn-start-review:active {
  transform: translateY(0);
  filter: brightness(1);
}

.btn-start-review:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
}

.btn-icon {
  width: 14px;
  height: 14px;
}

.btn-icon.spinning,
.loading-spin {
  animation: xy-review-spin 1s linear infinite;
}

.issues-loading,
.issues-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 32px 12px;
  color: var(--xy-text-4);
  font-size: var(--xy-fs-sm);
}

.loading-spin {
  width: 16px;
  height: 16px;
}

@keyframes xy-review-spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.right-panel {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: var(--xy-bg-page);
}

.detail-header {
  height: var(--xy-panel-header-h);
  border-bottom: 1px solid var(--xy-border-1);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  flex-shrink: 0;
}

.detail-title {
  font-size: var(--xy-fs-md);
  font-weight: 600;
  color: var(--xy-text-1);
  margin: 0;
}

.detail-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.detail-empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 12px;
  color: var(--xy-text-4);
}

.empty-icon {
  width: 48px;
  height: 48px;
  opacity: 0.3;
}

.empty-text {
  font-size: var(--xy-fs-sm);
  color: var(--xy-text-4);
  margin: 0;
}

.detail-content {
  flex: 1;
  overflow-y: auto;
  padding: 24px;
  scrollbar-gutter: stable;
}

.detail-section {
  margin-bottom: 24px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--xy-fs-sm);
  font-weight: 600;
  color: var(--xy-text-2);
  margin: 0 0 12px 0;
}

.section-icon {
  width: 14px;
  height: 14px;
  color: var(--xy-brand-500);
}

.description-text {
  font-size: var(--xy-fs-md);
  color: var(--xy-text-2);
  line-height: 1.7;
  margin: 0;
  padding: 12px 16px;
  background: var(--xy-surface-1);
  border-radius: var(--xy-radius-md);
  border: 1px solid var(--xy-border-1);
}

.original-text {
  padding: 16px;
  background: var(--xy-surface-1);
  border-radius: var(--xy-radius-md);
  border: 1px solid var(--xy-border-1);
  font-family: var(--xy-font-serif);
  font-size: var(--xy-fs-base);
  line-height: 1.9;
  color: var(--xy-text-editor);
}

.original-text p {
  margin: 0;
  text-indent: 2em;
}

.highlight-error {
  background: rgba(248, 113, 113, 0.12);
  border-bottom: 2px wavy var(--xy-danger);
  padding: 1px 2px;
  border-radius: 2px;
  color: var(--xy-danger);
}

.suggestion-text {
  padding: 16px;
  background: var(--xy-surface-1);
  border-radius: var(--xy-radius-md);
  border: 1px solid var(--xy-border-2);
  font-family: var(--xy-font-serif);
  font-size: var(--xy-fs-base);
  line-height: 1.9;
  color: var(--xy-text-editor);
  position: relative;
}

.suggestion-text::before {
  content: '';
  position: absolute;
  left: 0;
  top: 12px;
  bottom: 12px;
  width: 3px;
  background: var(--xy-success);
  border-radius: 0 2px 2px 0;
}

.suggestion-text p {
  margin: 0;
  text-indent: 2em;
}

.highlight-fix {
  background: rgba(52, 211, 153, 0.12);
  border-bottom: 2px solid var(--xy-success);
  padding: 1px 2px;
  border-radius: 2px;
  color: var(--xy-success);
}

.action-buttons {
  display: flex;
  gap: 12px;
  padding-top: 8px;
}

.btn-adopt,
.btn-ignore,
.btn-manual {
  flex: 1;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  border-radius: var(--xy-radius-md);
  font-size: var(--xy-fs-sm);
  font-weight: 500;
  font-family: var(--xy-font-sans);
  cursor: pointer;
  transition: all var(--xy-dur-sm) var(--xy-ease-standard);
}

.btn-adopt {
  background: var(--xy-success);
  color: var(--xy-text-inverse);
  border: none;
}

.btn-adopt:hover {
  filter: brightness(1.1);
  transform: translateY(-1px);
}

.btn-ignore {
  background: transparent;
  color: var(--xy-text-3);
  border: 1px solid var(--xy-border-2);
}

.btn-ignore:hover {
  background: var(--xy-surface-hover);
  color: var(--xy-text-2);
  border-color: var(--xy-border-error);
  color: var(--xy-danger);
}

.btn-manual {
  background: var(--xy-surface-2);
  color: var(--xy-text-2);
  border: 1px solid var(--xy-border-2);
}

.btn-manual:hover {
  background: var(--xy-surface-hover);
  border-color: var(--xy-brand-400);
  color: var(--xy-text-1);
}

.statusbar {
  height: var(--xy-statusbar-h);
  background: var(--xy-surface-3);
  border-top: 1px solid var(--xy-border-1);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  flex-shrink: 0;
}

.status-left,
.status-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.status-item {
  display: flex;
  align-items: center;
  gap: 6px;
}

.pulse-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--xy-brand-500);
  animation: xy-pulse-dot 2s ease-in-out infinite;
  display: inline-block;
}

.ai-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--xy-success);
  box-shadow: 0 0 6px rgba(52, 211, 153, 0.5);
  display: inline-block;
}

.status-text {
  font-size: var(--xy-fs-xs);
  color: var(--xy-text-3);
}

.status-divider {
  font-size: var(--xy-fs-xs);
  color: var(--xy-text-4);
}

@keyframes xy-pulse-dot {
  0% {
    box-shadow: 0 0 0 0 rgba(149, 133, 212, 0.5);
  }
  70% {
    box-shadow: 0 0 0 8px transparent;
  }
  100% {
    box-shadow: 0 0 0 0 transparent;
  }
}

@media (prefers-reduced-motion: reduce) {
  .pulse-dot {
    animation-duration: 0.01ms !important;
  }

  .tab-btn,
  .issue-card,
  .nav-icon-btn,
  .btn-start-review,
  .btn-adopt,
  .btn-ignore,
  .btn-manual {
    transition-duration: 0.01ms !important;
  }
}
</style>
