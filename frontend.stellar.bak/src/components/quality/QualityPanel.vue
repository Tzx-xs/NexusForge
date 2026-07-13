<template>
  <div class="quality-panel">
    <div class="panel-header">
      <div class="header-title">
        <n-icon size="18" :color="report ? (report.passed ? '#18a058' : '#d03050') : '#888'">
          <ShieldCheck />
        </n-icon>
        <span>质量护栏</span>
      </div>
      <n-space>
        <n-button size="tiny" type="primary" :loading="auditing" @click="runAudit_">
          检测
        </n-button>
      </n-space>
    </div>

    <div v-if="report" class="report-content">
      <div class="overall-score">
        <div class="score-circle" :style="{ '--score-color': scoreColor }">
          <span class="score-num">{{ report.overall_score }}</span>
        </div>
        <div class="score-info">
          <div class="score-label">综合质量分</div>
          <div class="score-status" :class="report.passed ? 'passed' : 'failed'">
            {{ report.passed ? '通过' : '需改进' }}
          </div>
          <div class="score-meta">
            <span>{{ report.total_issues }} 个问题</span>
            <span v-if="report.critical_issues > 0" class="critical">
              {{ report.critical_issues }} 严重
            </span>
          </div>
        </div>
      </div>

      <div class="guard-list">
        <div
          v-for="guard in report.guard_results"
          :key="guard.guard_name"
          class="guard-item"
          :class="{ expanded: expandedGuard === guard.guard_name }"
          @click="toggleGuard(guard.guard_name)"
        >
          <div class="guard-header">
            <div class="guard-name">
              <n-tag :type="guard.passed ? 'success' : 'warning'" size="small">
                {{ getGuardLabel(guard.guard_name) }}
              </n-tag>
            </div>
            <div class="guard-score">
              <n-progress
                type="line"
                :percentage="guard.score"
                :height="6"
                :color="getScoreColor(guard.score)"
                :rail-color="'#f0f0f0'"
                :show-indicator="false"
              />
              <span class="score-num">{{ Math.round(guard.score) }}</span>
            </div>
            <n-icon size="14" class="expand-icon">
              <ChevronDown />
            </n-icon>
          </div>

          <div
            v-if="expandedGuard === guard.guard_name && guard.issues.length > 0"
            class="guard-issues"
          >
            <div v-for="issue in guard.issues.slice(0, 5)" :key="issue.message" class="issue-item">
              <div class="issue-severity">
                <n-tag :type="getSeverityType(issue.severity)" size="tiny">
                  {{ getSeverityLabel(issue.severity) }}
                </n-tag>
              </div>
              <div class="issue-content">
                <div class="issue-message">{{ issue.message }}</div>
                <div v-if="issue.suggestion" class="issue-suggestion">
                  建议：{{ issue.suggestion }}
                </div>
                <div v-if="issue.paragraph_index !== undefined" class="issue-location">
                  第 {{ issue.paragraph_index + 1 }} 段
                </div>
              </div>
            </div>
            <div v-if="guard.issues.length > 5" class="more-issues">
              还有 {{ guard.issues.length - 5 }} 个问题
            </div>
          </div>

          <div
            v-if="expandedGuard === guard.guard_name && guard.issues.length === 0"
            class="no-issues"
          >
            <n-text depth="3">本项检测通过，无问题</n-text>
          </div>
        </div>
      </div>
    </div>

    <div v-else class="empty-state">
      <n-empty description="点击检测按钮开始质量审查" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { NButton, NSpace, NTag, NProgress, NEmpty, NIcon, NText } from 'naive-ui'
import { ShieldCheck, ChevronDown } from '@vicons/tabler'
import { runAudit, type AuditReport } from '@/api/quality'

const props = defineProps<{
  content: string
  context?: Record<string, any>
}>()

const auditing = ref(false)
const report = ref<AuditReport | null>(null)
const expandedGuard = ref<string | null>(null)

const scoreColor = computed(() => {
  if (!report.value) return '#888'
  const s = report.value.overall_score
  if (s >= 80) return '#18a058'
  if (s >= 60) return '#f0a020'
  return '#d03050'
})

function getScoreColor(score: number) {
  if (score >= 80) return '#18a058'
  if (score >= 60) return '#f0a020'
  return '#d03050'
}

function getSeverityType(severity: string) {
  switch (severity) {
    case 'critical':
    case 'error':
      return 'error'
    case 'warning':
      return 'warning'
    case 'info':
    default:
      return 'info'
  }
}

function getSeverityLabel(severity: string) {
  switch (severity) {
    case 'critical':
      return '严重'
    case 'error':
      return '错误'
    case 'warning':
      return '警告'
    case 'info':
      return '提示'
    default:
      return severity
  }
}

const guardLabels: Record<string, string> = {
  character_consistency: '角色一致性',
  plot_density: '情节密度',
  language_style: '语言风格',
  rhythm: '节奏把控',
  pov: '视角统一',
  naming_consistency: '命名一致性',
  anti_ai: '反 AI 味',
  macro_rhythm: '宏观节奏',
}

function getGuardLabel(name: string) {
  return guardLabels[name] || name
}

function toggleGuard(name: string) {
  expandedGuard.value = expandedGuard.value === name ? null : name
}

async function runAudit_() {
  if (!props.content) return
  auditing.value = true
  try {
    const res = await runAudit({
      content: props.content,
      context: props.context,
    })
    report.value = res
    if (res.guard_results.length > 0) {
      expandedGuard.value = res.guard_results[0].guard_name
    }
  } finally {
    auditing.value = false
  }
}

defineExpose({
  runAudit: runAudit_,
})
</script>

<style scoped>
.quality-panel {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #fff;
}

.panel-header {
  padding: 12px 16px;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-shrink: 0;
}

.header-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
}

.report-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.overall-score {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
  padding: 16px;
  background: #fafafa;
  border-radius: 8px;
}

.score-info {
  flex: 1;
}

.score-label {
  font-size: 13px;
  color: #666;
  margin-bottom: 4px;
}

.score-status {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 4px;
}

.score-status.passed {
  color: #18a058;
}

.score-status.failed {
  color: #d03050;
}

.score-meta {
  font-size: 12px;
  color: #999;
  display: flex;
  gap: 12px;
}

.score-meta .critical {
  color: #d03050;
}

.guard-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.guard-item {
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  overflow: hidden;
  cursor: pointer;
  transition: border-color 0.2s;
}

.guard-item:hover {
  border-color: #2080f0;
}

.guard-item.expanded {
  border-color: #2080f0;
}

.guard-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  background: #fafafa;
}

.guard-name {
  flex-shrink: 0;
  width: 100px;
}

.guard-score {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
}

.score-num {
  font-size: 12px;
  color: #666;
  width: 32px;
  text-align: right;
  flex-shrink: 0;
}

.expand-icon {
  flex-shrink: 0;
  transition: transform 0.2s;
  color: #999;
}

.guard-item.expanded .expand-icon {
  transform: rotate(180deg);
}

.guard-issues {
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.issue-item {
  display: flex;
  gap: 8px;
  font-size: 12px;
}

.issue-severity {
  flex-shrink: 0;
}

.issue-content {
  flex: 1;
}

.issue-message {
  color: #333;
  margin-bottom: 4px;
  line-height: 1.5;
}

.issue-suggestion {
  color: #18a058;
  margin-bottom: 2px;
}

.issue-location {
  color: #999;
  font-size: 11px;
}

.more-issues {
  text-align: center;
  color: #999;
  font-size: 11px;
  padding-top: 4px;
}

.no-issues {
  padding: 16px;
  text-align: center;
}

.empty-state {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
