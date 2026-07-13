<template>
  <div class="module-panel content-review-panel">
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
          <div class="hero-eyebrow">质量把关</div>
          <h1 class="hero-title">内容审查</h1>
          <p class="hero-desc">让 AI 帮你识别逻辑漏洞、文风问题与潜在风险，守护每一章的完整性。</p>
        </div>
        <button class="btn-new-review" @click="openCreateModal">
          <Plus class="icon-14"/>
          新建审查
        </button>
      </header>

      <!-- 统计横条 -->
      <div class="stats-bar">
        <div class="stat-pill">
          <span class="stat-value">{{ tasks.length }}</span>
          <span class="stat-label">任务总数</span>
        </div>
        <div class="stat-pill">
          <span class="stat-value">{{ pendingCount }}</span>
          <span class="stat-label">待处理</span>
        </div>
        <div class="stat-pill">
          <span class="stat-value">{{ completedCount }}</span>
          <span class="stat-label">已完成</span>
        </div>
      </div>

      <!-- 骨架屏 -->
      <div v-if="loading" class="skeleton-list">
        <div v-for="i in 5" :key="i" class="skeleton-row shimmer"/>
      </div>

      <!-- 空状态 -->
      <div v-else-if="tasks.length === 0" class="empty-state">
        <div class="empty-constellation">
          <div class="orbit orbit-1"/>
          <div class="orbit orbit-2"/>
          <div class="empty-star">
            <ShieldCheck class="icon-40"/>
          </div>
        </div>
        <h3 class="empty-title">暂无审查任务</h3>
        <p class="empty-desc">创建第一个审查任务，开始校验章节质量</p>
        <button class="empty-btn" @click="openCreateModal">
          <Plus class="icon-14"/>
          新建审查
        </button>
      </div>

      <!-- 任务列表 -->
      <section v-else class="review-section">
        <div class="review-toolbar">
          <span class="review-count">共 {{ tasks.length }} 项任务</span>
        </div>

        <div class="review-list">
          <article
            v-for="task in tasks"
            :key="task.id"
            class="review-card"
          >
            <div class="review-main">
              <div class="review-title-row">
                <span class="review-title">{{ task.title }}</span>
                <span class="status-badge" :class="task.status">
                  <component :is="statusIcon(task.status)" class="status-icon"/>
                  {{ statusLabel(task.status) }}
                </span>
              </div>
              <div class="review-meta">
                <span class="meta-time">{{ formatTime(task.created_at) }}</span>
                <span v-if="task.novel_id" class="meta-novel">小说 ID: {{ task.novel_id }}</span>
              </div>
              <div v-if="task.result" class="review-result">
                {{ previewResult(task.result) }}
              </div>
            </div>
            <button
              class="review-delete"
              title="删除"
              @click="handleDelete(task.id)"
            >
              <Trash class="icon-16"/>
            </button>
          </article>
        </div>
      </section>
    </div>

    <XyDialog v-model="showCreateModal" title="新建审查任务">
      <div class="create-form">
        <div class="form-row">
          <label class="form-label">审查标题</label>
          <input
            v-model="newTitle"
            type="text"
            class="form-input"
            placeholder="请输入审查标题"
            @keydown.enter="submitCreate"
          />
        </div>
        <div class="form-row">
          <label class="form-label">关联小说 ID（可选）</label>
          <input
            v-model="newNovelId"
            type="text"
            class="form-input"
            placeholder="输入小说 ID"
          />
        </div>
      </div>
      <template #footer>
        <button class="cr-dialog-btn cr-dialog-btn-secondary" @click="showCreateModal = false">
          取消
        </button>
        <button
          class="cr-dialog-btn cr-dialog-btn-primary"
          :disabled="!newTitle.trim()"
          @click="submitCreate"
        >
          创建
        </button>
      </template>
    </XyDialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ShieldCheck, Plus, Trash, Clock, Check, AlertCircle } from '@vicons/tabler'
import { XyDialog } from '@/components/common'
import {
  createReviewTask,
  deleteReviewTask,
  listReviewTasks,
  type ReviewTask,
} from '@/api/review'
import { toast } from '@/utils/toast'

const tasks = ref<ReviewTask[]>([])
const loading = ref(false)
const showCreateModal = ref(false)
const newTitle = ref('')
const newNovelId = ref('')

const pendingCount = computed(() => tasks.value.filter((t) => t.status === 'pending').length)
const completedCount = computed(() => tasks.value.filter((t) => t.status === 'completed').length)

async function loadTasks() {
  loading.value = true
  try {
    const res = await listReviewTasks()
    tasks.value = res.items || []
  } finally {
    loading.value = false
  }
}

function openCreateModal() {
  newTitle.value = ''
  newNovelId.value = ''
  showCreateModal.value = true
}

async function submitCreate() {
  const title = newTitle.value.trim()
  if (!title) return
  try {
    await createReviewTask(title, newNovelId.value.trim() || undefined)
    toast.success('审查任务创建成功')
    showCreateModal.value = false
    await loadTasks()
  } catch {
    // 错误已由 http 拦截器提示
  }
}

async function handleDelete(taskId: string) {
  try {
    await deleteReviewTask(taskId)
    toast.success('已删除')
    await loadTasks()
  } catch {
    // 错误已由 http 拦截器提示
  }
}

function statusIcon(status: string) {
  switch (status) {
    case 'completed':
      return Check
    case 'failed':
      return AlertCircle
    default:
      return Clock
  }
}

function statusLabel(status: string) {
  switch (status) {
    case 'pending':
      return '待处理'
    case 'completed':
      return '已完成'
    case 'failed':
      return '失败'
    default:
      return status
  }
}

function formatTime(iso: string) {
  if (!iso) return '-'
  try {
    return new Date(iso).toLocaleString('zh-CN')
  } catch {
    return iso
  }
}

function previewResult(result: string) {
  const max = 120
  if (!result) return ''
  return result.length > max ? `${result.slice(0, max)}...` : result
}

onMounted(() => {
  loadTasks()
})
</script>

<style scoped>
.content-review-panel {
  position: relative;
  min-height: 100%;
  animation: xy-fade-in var(--xy-dur-md) var(--xy-ease-standard);
}

.panel-inner {
  position: relative;
  max-width: 880px;
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
  opacity: 0.1;
}

.nebula-1 {
  width: 600px;
  height: 600px;
  top: -200px;
  right: -160px;
  background: radial-gradient(circle, var(--xy-brand-400) 0%, transparent 70%);
  animation: nebula-drift 22s ease-in-out infinite alternate;
}

.nebula-2 {
  width: 420px;
  height: 420px;
  bottom: -100px;
  left: -100px;
  background: radial-gradient(circle, var(--xy-accent-soft) 0%, transparent 70%);
  animation: nebula-drift 28s ease-in-out infinite alternate-reverse;
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
  gap: 24px;
  margin-bottom: 28px;
  flex-wrap: wrap;
}

.hero-text {
  flex: 1;
  min-width: 280px;
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
  font-size: clamp(28px, 4vw, 42px);
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
  max-width: 480px;
}

.btn-new-review {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 10px 18px;
  border-radius: var(--xy-radius-md, 8px);
  border: none;
  background: linear-gradient(135deg, var(--xy-accent), #e8c46a);
  color: #1a1525;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--xy-dur-sm);
  flex-shrink: 0;
}

.btn-new-review:hover {
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

/* Skeleton */
.skeleton-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  animation: section-rise 0.5s var(--xy-ease-standard) forwards;
}

.skeleton-row {
  height: 96px;
  border-radius: var(--xy-radius-lg, 10px);
  background: linear-gradient(
    90deg,
    var(--xy-surface-2) 25%,
    var(--xy-surface-3) 37%,
    var(--xy-surface-2) 63%
  );
  background-size: 400% 100%;
  animation: xy-shimmer 1.5s ease-in-out infinite;
}

/* Review Section */
.review-section {
  animation: section-rise 0.6s var(--xy-ease-standard) forwards;
}

.review-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 20px;
  min-height: 28px;
}

.review-count {
  font-size: 13px;
  color: var(--xy-text-3);
  letter-spacing: 0.02em;
}

.review-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.review-card {
  background: var(--xy-surface-1);
  border: 1px solid var(--xy-border-1);
  border-radius: var(--xy-radius-lg, 10px);
  padding: 18px 20px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  box-shadow: var(--xy-shadow-sm);
  transition: all var(--xy-dur-sm);
}

.review-card:hover {
  border-color: var(--xy-border-2);
  box-shadow: var(--xy-shadow-md);
  transform: translateY(-1px);
}

.review-main {
  flex: 1;
  min-width: 0;
}

.review-title-row {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 8px;
  flex-wrap: wrap;
}

.review-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--xy-text-1);
}

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 3px 9px;
  border-radius: var(--xy-radius-full, 9999px);
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.03em;
  text-transform: uppercase;
}

.status-badge.pending {
  background: rgba(212, 168, 83, 0.12);
  color: var(--xy-accent);
}

.status-badge.completed {
  background: rgba(74, 222, 128, 0.12);
  color: var(--xy-success);
}

.status-badge.failed {
  background: rgba(248, 113, 113, 0.12);
  color: var(--xy-danger);
}

.status-icon {
  width: 12px;
  height: 12px;
}

.review-meta {
  font-size: 12px;
  color: var(--xy-text-3);
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 10px;
}

.meta-novel {
  color: var(--xy-text-2);
}

.review-result {
  font-size: 13px;
  color: var(--xy-text-2);
  line-height: 1.65;
  background: var(--xy-surface-2);
  padding: 10px 14px;
  border-radius: var(--xy-radius-md, 8px);
  word-break: break-all;
  border-left: 2px solid var(--xy-brand-500);
}

.review-delete {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 30px;
  height: 30px;
  border-radius: var(--xy-radius-md, 8px);
  border: 1px solid var(--xy-border-1);
  background: var(--xy-surface-2);
  color: var(--xy-text-3);
  cursor: pointer;
  transition: all var(--xy-dur-sm);
  flex-shrink: 0;
}

.review-delete:hover {
  color: var(--xy-danger);
  border-color: var(--xy-danger);
  background: var(--xy-danger-bg);
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
  color: var(--xy-brand-500);
  box-shadow: 0 0 32px rgba(139, 126, 200, 0.12);
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

/* Create Modal Form */
.create-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form-row {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-label {
  font-size: 12px;
  font-weight: 500;
  color: var(--xy-text-2);
}

.form-input {
  width: 100%;
  padding: 10px 12px;
  border-radius: var(--xy-radius-md, 8px);
  border: 1px solid var(--xy-border-1);
  background: var(--xy-surface-2);
  color: var(--xy-text-1);
  font-size: 13px;
  font-family: var(--xy-font-sans);
  outline: none;
  transition: all var(--xy-dur-sm);
}

.form-input:hover {
  border-color: var(--xy-border-2);
  background: var(--xy-surface-hover);
}

.form-input:focus {
  border-color: var(--xy-border-focus);
  box-shadow: var(--xy-shadow-focus-ring);
  background: var(--xy-surface-hover);
}

.form-input::placeholder {
  color: var(--xy-text-4);
}

/* Dialog footer buttons */
.cr-dialog-btn {
  height: 32px;
  padding: 0 var(--xy-space-5, 20px);
  border-radius: var(--xy-radius-md, 8px);
  font-size: var(--xy-fs-sm, 13px);
  font-weight: var(--xy-fw-med, 500);
  font-family: var(--xy-font-sans);
  cursor: pointer;
  transition: all var(--xy-dur-sm);
}

.cr-dialog-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none !important;
}

.cr-dialog-btn-secondary {
  background: transparent;
  border: 1px solid var(--xy-border-1);
  color: var(--xy-text-2);
}

.cr-dialog-btn-secondary:hover {
  background: var(--xy-surface-2);
}

.cr-dialog-btn-primary {
  background: var(--xy-brand-500);
  border: none;
  color: var(--xy-text-inverse);
  font-weight: var(--xy-fw-sb, 600);
}

.cr-dialog-btn-primary:hover:not(:disabled) {
  background: var(--xy-brand-400);
  transform: translateY(-1px);
}

/* Utilities */
.icon-14 {
  width: 14px;
  height: 14px;
}

.icon-16 {
  width: 16px;
  height: 16px;
}

.icon-40 {
  width: 40px;
  height: 40px;
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

@keyframes orbit-rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Responsive */
@media (max-width: 768px) {
  .panel-inner {
    padding: 24px 16px 40px;
  }

  .hero-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 18px;
  }

  .stats-bar {
    gap: 10px;
  }

  .stat-pill {
    padding: 8px 14px;
  }

  .review-card {
    padding: 14px 16px;
  }

  .review-title-row {
    gap: 8px;
  }
}
</style>
