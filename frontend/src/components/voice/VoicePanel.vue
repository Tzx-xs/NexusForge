<template>
  <div class="voice-panel">
    <div class="panel-header">
      <div class="header-title">
        <n-icon size="18" color="#722ed1">
          <Microphone />
        </n-icon>
        <span>文风指纹</span>
      </div>
      <n-space>
        <n-button
          size="tiny"
          :disabled="!content"
          :loading="extracting"
          @click="extractFromContent"
        >
          提取指纹
        </n-button>
      </n-space>
    </div>

    <div class="panel-body">
      <div class="tabs">
        <div
          v-for="tab in tabs"
          :key="tab.key"
          class="tab-item"
          :class="{ active: activeTab === tab.key }"
          @click="activeTab = tab.key"
        >
          {{ tab.label }}
        </div>
      </div>

      <div v-if="activeTab === 'fingerprint'" class="tab-content">
        <div v-if="fingerprint" class="fingerprint-view">
          <div class="fp-header">
            <div class="fp-name">{{ fingerprint.name }}</div>
            <div class="fp-meta">
              <span>{{ fingerprint.source_sample_count }} 样本</span>
              <span>{{ fingerprint.source_char_count }} 字</span>
            </div>
          </div>

          <div class="metric-grid">
            <div class="metric-card">
              <div class="metric-label">词汇丰富度</div>
              <div class="metric-value">{{ (fingerprint.lexical_richness * 100).toFixed(1) }}%</div>
            </div>
            <div class="metric-card">
              <div class="metric-label">平均句长</div>
              <div class="metric-value">{{ fingerprint.sentence_length_mean.toFixed(1) }} 字</div>
            </div>
            <div class="metric-card">
              <div class="metric-label">句长变异</div>
              <div class="metric-value">{{ fingerprint.sentence_length_std.toFixed(1) }}</div>
            </div>
            <div class="metric-card">
              <div class="metric-label">平均段长</div>
              <div class="metric-value">{{ fingerprint.paragraph_length_mean.toFixed(0) }} 字</div>
            </div>
            <div class="metric-card">
              <div class="metric-label">对话占比</div>
              <div class="metric-value">{{ (fingerprint.dialogue_ratio * 100).toFixed(1) }}%</div>
            </div>
            <div class="metric-card">
              <div class="metric-label">虚词占比</div>
              <div class="metric-value">
                {{ (fingerprint.function_word_ratio * 100).toFixed(1) }}%
              </div>
            </div>
          </div>

          <div v-if="fingerprint.signature_phrases.length > 0" class="section">
            <div class="section-title">特色表达</div>
            <div class="phrase-list">
              <n-tag v-for="(p, i) in fingerprint.signature_phrases" :key="p + i" size="small">
                {{ p }}
              </n-tag>
            </div>
          </div>

          <div class="section">
            <div class="section-title">标点密度</div>
            <div class="punct-chart">
              <div v-for="(val, key) in topPunctuations" :key="key" class="punct-item">
                <span class="punct-mark">{{ key }}</span>
                <n-progress
                  type="line"
                  :percentage="val * 1000"
                  :height="4"
                  :show-indicator="false"
                  color="#722ed1"
                  rail-color="#f0f0f0"
                />
              </div>
            </div>
          </div>
        </div>

        <div v-else class="empty-state">
          <n-empty description="提取文风指纹以分析写作风格" />
        </div>
      </div>

      <div v-if="activeTab === 'drift'" class="tab-content">
        <div v-if="driftResult" class="drift-view">
          <div class="drift-overall">
            <div
              class="score-circle"
              :style="{ '--score-color': driftResult.drifted ? '#f0a020' : '#18a058' }"
            >
              <span class="score-num">{{ Math.round(driftResult.overall_similarity * 100) }}</span>
            </div>
            <div class="drift-info">
              <div class="drift-label">文风相似度</div>
              <div class="drift-status" :class="driftResult.drifted ? 'drifted' : 'consistent'">
                {{ driftResult.drifted ? '文风漂移' : '风格一致' }}
              </div>
            </div>
          </div>

          <div class="drift-dimensions">
            <div class="section-title">维度详情</div>
            <div v-for="(score, dim) in driftResult.dimension_scores" :key="dim" class="dim-item">
              <span class="dim-label">{{ getDimLabel(dim as string) }}</span>
              <n-progress
                type="line"
                :percentage="score * 100"
                :height="6"
                :show-indicator="false"
                :color="getDimColor(score)"
                :rail-color="'#f0f0f0'"
              />
              <span class="dim-score">{{ (score * 100).toFixed(0) }}%</span>
            </div>
          </div>

          <div v-if="driftResult.drift_dimensions.length > 0" class="drift-actions">
            <n-button size="small" type="primary" @click="generateRewrite"> 生成重写提示 </n-button>
          </div>
        </div>

        <div v-else class="empty-state">
          <n-empty description="与基准指纹对比检测文风漂移" />
        </div>
      </div>

      <div v-if="activeTab === 'guide'" class="tab-content">
        <div v-if="styleGuide" class="guide-view">
          <n-card
            size="small"
            content-style="white-space: pre-wrap; font-family: monospace; font-size: 12px;"
          >
            {{ styleGuide }}
          </n-card>
        </div>
        <div v-else class="empty-state">
          <n-empty description="生成风格指南以保持文风一致" />
        </div>
      </div>
    </div>

    <n-modal v-model:show="showRewritePrompt" preset="card" title="重写提示" style="width: 500px">
      <div v-if="rewritePrompt" style="white-space: pre-wrap; font-size: 13px; line-height: 1.6">
        {{ rewritePrompt }}
      </div>
      <template #footer>
        <n-space justify="end">
          <n-button @click="showRewritePrompt = false">关闭</n-button>
          <n-button type="primary" @click="copyRewritePrompt">复制</n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import {
  NButton,
  NSpace,
  NIcon,
  NTag,
  NProgress,
  NEmpty,
  NCard,
  NModal,
  useMessage,
} from 'naive-ui'
import { Microphone } from '@vicons/tabler'
import {
  extractFingerprint,
  detectDrift as apiDetectDrift,
  generateRewritePrompt as apiRewritePrompt,
  getStyleGuide as apiGetStyleGuide,
  type VoiceFingerprint,
  type VoiceDriftResult,
} from '@/api/voice'

const props = defineProps<{
  content: string
  baselineFpId?: string
}>()

const message = useMessage()

const extracting = ref(false)
const detecting = ref(false)
const fingerprint = ref<VoiceFingerprint | null>(null)
const driftResult = ref<VoiceDriftResult | null>(null)
const styleGuide = ref('')
const showRewritePrompt = ref(false)
const rewritePrompt = ref('')

const activeTab = ref<'fingerprint' | 'drift' | 'guide'>('fingerprint')

const tabs: { key: 'fingerprint' | 'drift' | 'guide'; label: string }[] = [
  { key: 'fingerprint', label: '指纹' },
  { key: 'drift', label: '漂移检测' },
  { key: 'guide', label: '风格指南' },
]

const dimLabels: Record<string, string> = {
  lexical_richness: '词汇丰富度',
  sentence_length_mean: '平均句长',
  sentence_length_std: '句长变异',
  paragraph_length_mean: '段落长度',
  dialogue_ratio: '对话占比',
  function_word_ratio: '虚词比例',
  punctuation_density: '标点密度',
  ngram_overlap: '常用语重合',
}

function getDimLabel(dim: string) {
  return dimLabels[dim] || dim
}

function getDimColor(score: number) {
  if (score >= 0.8) return '#18a058'
  if (score >= 0.6) return '#f0a020'
  return '#d03050'
}

const topPunctuations = computed(() => {
  if (!fingerprint.value) return {}
  const entries = Object.entries(fingerprint.value.punctuation_density)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6)
  return Object.fromEntries(entries)
})

async function extractFromContent() {
  if (!props.content) return
  extracting.value = true
  try {
    const res = await extractFingerprint([props.content], 'current_sample')
    fingerprint.value = res
    message.success('文风指纹提取完成')

    if (props.baselineFpId) {
      await runDriftDetection()
    }

    const guideRes = await apiGetStyleGuide(res.fingerprint_id)
    styleGuide.value = guideRes.style_guide
  } finally {
    extracting.value = false
  }
}

async function runDriftDetection() {
  if (!props.baselineFpId || !props.content) return
  detecting.value = true
  try {
    const res = await apiDetectDrift(props.baselineFpId, props.content)
    driftResult.value = res
  } finally {
    detecting.value = false
  }
}

async function generateRewrite() {
  if (!props.baselineFpId || !props.content || !driftResult.value) return
  const res = await apiRewritePrompt(
    props.baselineFpId,
    props.content,
    driftResult.value.drift_dimensions
  )
  rewritePrompt.value = res.prompt
  showRewritePrompt.value = true
}

function copyRewritePrompt() {
  navigator.clipboard.writeText(rewritePrompt.value)
  message.success('已复制到剪贴板')
}
</script>

<style scoped>
.voice-panel {
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

.panel-body {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.tabs {
  display: flex;
  padding: 8px 12px;
  gap: 4px;
  border-bottom: 1px solid #f0f0f0;
  flex-shrink: 0;
}

.tab-item {
  padding: 6px 12px;
  font-size: 13px;
  color: #666;
  cursor: pointer;
  border-radius: 6px;
  transition: all 0.2s;
}

.tab-item:hover {
  background: #f5f5f5;
}

.tab-item.active {
  background: #e8f3ff;
  color: #2080f0;
  font-weight: 500;
}

.tab-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
}

.fp-header {
  margin-bottom: 16px;
}

.fp-name {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 4px;
}

.fp-meta {
  font-size: 12px;
  color: #999;
  display: flex;
  gap: 16px;
}

.metric-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
  margin-bottom: 16px;
}

.metric-card {
  background: #fafafa;
  padding: 10px 12px;
  border-radius: 6px;
}

.metric-label {
  font-size: 11px;
  color: #999;
  margin-bottom: 4px;
}

.metric-value {
  font-size: 16px;
  font-weight: 600;
  color: #333;
}

.section {
  margin-bottom: 16px;
}

.section-title {
  font-size: 12px;
  color: #666;
  margin-bottom: 8px;
  font-weight: 500;
}

.phrase-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.punct-chart {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.punct-item {
  display: flex;
  align-items: center;
  gap: 8px;
}

.punct-mark {
  width: 20px;
  font-size: 14px;
  text-align: center;
}

.punct-item .n-progress {
  flex: 1;
}

.drift-overall {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
  padding: 16px;
  background: #fafafa;
  border-radius: 8px;
}

.drift-info {
  flex: 1;
}

.drift-label {
  font-size: 13px;
  color: #666;
  margin-bottom: 4px;
}

.drift-status {
  font-size: 16px;
  font-weight: 600;
}

.drift-status.drifted {
  color: #f0a020;
}

.drift-status.consistent {
  color: #18a058;
}

.drift-dimensions {
  margin-bottom: 16px;
}

.dim-item {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.dim-label {
  width: 80px;
  font-size: 12px;
  color: #666;
  flex-shrink: 0;
}

.dim-item .n-progress {
  flex: 1;
}

.dim-score {
  width: 40px;
  font-size: 12px;
  color: #999;
  text-align: right;
  flex-shrink: 0;
}

.drift-actions {
  text-align: center;
  padding-top: 8px;
}

.empty-state {
  height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
}
</style>
