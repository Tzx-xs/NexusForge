<template>
  <div class="ai-console">
    <div class="console-header">
      <span class="console-title">AI 控制台</span>
      <div class="console-tabs">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          class="tab-btn"
          :class="{ active: activeTab === tab.key }"
          @click="activeTab = tab.key"
        >
          {{ tab.label }}
        </button>
      </div>
    </div>

    <div class="console-body">
      <div v-if="activeTab === 'generate'" class="tab-content">
        <div class="generate-section">
          <div class="section-title">生成模式</div>
          <div class="mode-selector">
            <button
              v-for="mode in generateModes"
              :key="mode.value"
              class="mode-btn"
              :class="{ active: selectedMode === mode.value }"
              @click="selectedMode = mode.value"
            >
              <component :is="mode.icon" class="mode-icon" />
              <span>{{ mode.label }}</span>
            </button>
          </div>
        </div>

        <div class="generate-section">
          <div class="section-title">生成参数</div>
          <div class="param-item">
            <label>章节长度</label>
            <n-select v-model:value="targetLength" :options="lengthOptions" size="small" />
          </div>
          <div class="param-item">
            <label>风格强度</label>
            <n-slider v-model:value="styleStrength" :min="0" :max="100" />
          </div>
          <div class="param-item">
            <label>随机性</label>
            <n-slider v-model:value="creativity" :min="0" :max="100" />
          </div>
        </div>

        <div class="generate-section">
          <div class="section-title">质量护栏</div>
          <div class="guard-list">
            <div v-for="guard in qualityGuards" :key="guard.id" class="guard-item">
              <span class="guard-name">{{ guard.name }}</span>
              <n-switch v-model:value="guard.enabled" size="small" />
            </div>
          </div>
        </div>

        <div class="generate-actions">
          <button class="generate-btn" :disabled="isGenerating" @click="handleGenerate">
            <PlayerPlay class="btn-icon" />
            {{ isGenerating ? '生成中…' : '开始生成' }}
          </button>
          <button class="auto-btn" :class="{ running: autopilotRunning }" @click="toggleAutopilot">
            <Robot class="btn-icon" />
            {{ autopilotRunning ? '停止驾驶' : '自动驾驶' }}
          </button>
          <div v-if="autopilotRunning && autopilotProgress" class="autopilot-progress">
            进度：{{ autopilotProgress.current }} / {{ autopilotProgress.total }} 章 ·
            {{ autopilotProgress.words }} 字
          </div>
        </div>
      </div>

      <div v-if="activeTab === 'quality'" class="tab-content-full">
        <QualityPanel ref="qualityPanelRef" :content="content" :context="qualityContext" />
      </div>

      <div v-if="activeTab === 'voice'" class="tab-content-full">
        <VoicePanel :content="content" :baseline-fp-id="baselineFpId" />
      </div>

      <div v-if="activeTab === 'ironlock'" class="tab-content">
        <IronLockPanel />
      </div>

      <div v-if="activeTab === 'foreshadow'" class="tab-content">
        <ForeshadowPanel />
      </div>

      <div v-if="activeTab === 'history'" class="tab-content">
        <div class="history-empty">暂无生成历史</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, markRaw, computed, onBeforeUnmount } from 'vue'
import { useRoute } from 'vue-router'
import { PlayerPlay, Robot, Shield, Ban, Star, MessageCircle } from '@vicons/tabler'
import { NSelect, NSwitch, NSlider } from 'naive-ui'
import QualityPanel from '@/components/quality/QualityPanel.vue'
import VoicePanel from '@/components/voice/VoicePanel.vue'
import IronLockPanel from './IronLockPanel.vue'
import ForeshadowPanel from './ForeshadowPanel.vue'
import { getGenerateContentUrl, getAuthHeaders } from '@/api/chapters'
import { createSession, startSession, getSession, cancelSession } from '@/api/autonomous'
import { toast } from '@/utils/toast'
import { parseSseBlocks, type SseEvent } from '@/utils/sseParser'
import { createTimeoutSignal, combineAbortSignals } from '@/utils/abortSignalPolyfill'

const route = useRoute()

const props = defineProps<{
  content: string
  chapterId?: string
  characterNames?: string[]
  locationNames?: string[]
  baselineFpId?: string
}>()

const emit = defineEmits<{
  (e: 'update:content', value: string): void
  (e: 'generated', value: string): void
}>()

const tabs = [
  { key: 'generate', label: '生成' },
  { key: 'quality', label: '质检' },
  { key: 'voice', label: '文风' },
  { key: 'ironlock', label: '铁锁' },
  { key: 'foreshadow', label: '伏笔' },
  { key: 'history', label: '历史' },
]

const qualityPanelRef = ref<InstanceType<typeof QualityPanel> | null>(null)

const activeTab = ref('generate')
const selectedMode = ref('continue')

const generateModes = [
  { value: 'continue', label: '续写', icon: markRaw(Star) },
  { value: 'rewrite', label: '改写', icon: markRaw(MessageCircle) },
  { value: 'expand', label: '扩写', icon: markRaw(Ban) },
  { value: 'guard', label: '守护', icon: markRaw(Shield) },
]

const targetLength = ref('medium')
const lengthOptions = [
  { label: '短 (1500字)', value: 'short' },
  { label: '中 (3000字)', value: 'medium' },
  { label: '长 (5000字)', value: 'long' },
]

const styleStrength = ref(70)
const creativity = ref(50)

const qualityGuards = ref([
  { id: 'character', name: '角色一致性', enabled: true },
  { id: 'plot', name: '情节密度', enabled: true },
  { id: 'style', name: '语言风格', enabled: true },
  { id: 'rhythm', name: '节奏把控', enabled: true },
  { id: 'antiAi', name: '反AI味', enabled: true },
  { id: 'pov', name: '视角统一', enabled: false },
])

const qualityContext = computed(() => ({
  character_names: props.characterNames || [],
  location_names: props.locationNames || [],
  chapter_id: props.chapterId,
}))

const isGenerating = ref(false)
const generateProgress = ref(0)
let generateAbort: AbortController | null = null

function handleSseEvent(
  evt: SseEvent,
  baseContent: string,
  generatedRef: { value: string }
): 'complete' | 'error' | null {
  let payload: Record<string, unknown> = {}
  if (evt.data) {
    try {
      payload = JSON.parse(evt.data)
    } catch {
      payload = {}
    }
  }
  switch (evt.event) {
    case 'token': {
      const token =
        (payload.delta as string) || (payload.token as string) || (payload.content as string) || ''
      if (token) {
        generatedRef.value += token
        emit('update:content', baseContent + generatedRef.value)
      }
      break
    }
    case 'progress': {
      const percent = Number(payload.percent)
      if (!Number.isNaN(percent)) {
        generateProgress.value = percent
      }
      break
    }
    case 'complete':
      return 'complete'
    case 'error': {
      const message = (payload.message as string) || '生成失败'
      toast.error(message)
      return 'error'
    }
  }
  return null
}

async function handleGenerate() {
  if (isGenerating.value) return
  const chapterId = props.chapterId || (route.params.chapterId as string)
  if (!chapterId) {
    toast.error('未选中章节，无法生成')
    return
  }
  isGenerating.value = true
  generateProgress.value = 0
  generateAbort = new AbortController()
  // M-02: 统一 120 秒 SSE 超时，与用户取消的 AbortController 合并
  const { signal: timeoutSignal, cleanup: timeoutCleanup } = createTimeoutSignal(120_000)
  const { signal: combinedSignal, cleanup: combineCleanup } = combineAbortSignals([generateAbort.signal, timeoutSignal])
  const baseContent = props.content || ''
  const generatedRef = { value: '' }
  let terminal: 'complete' | 'error' | null = null
  try {
    const url = getGenerateContentUrl(chapterId)
    const response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
        ...getAuthHeaders(),
      },
      signal: combinedSignal,
      body: JSON.stringify({
        mode: selectedMode.value,
        target_length: targetLength.value,
        style_strength: styleStrength.value,
        creativity: creativity.value,
        quality_guards: qualityGuards.value.filter((g) => g.enabled).map((g) => g.id),
        context: baseContent,
      }),
    })
    if (!response.ok || !response.body) {
      let msg = `生成失败：HTTP ${response.status}`
      try {
        const errBody = await response.json()
        if (errBody?.detail) msg = errBody.detail
        else if (errBody?.message) msg = errBody.message
      } catch {
        // 忽略 JSON 解析失败
      }
      throw new Error(msg)
    }
    const reader = response.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''
    while (terminal === null) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, '\n')
      const lastSep = buffer.lastIndexOf('\n\n')
      if (lastSep === -1) continue
      const ready = buffer.slice(0, lastSep + 2)
      buffer = buffer.slice(lastSep + 2)
      for (const evt of parseSseBlocks(ready)) {
        terminal = handleSseEvent(evt, baseContent, generatedRef)
        if (terminal !== null) break
      }
    }
    // 处理尾部残留
    const tail = decoder.decode()
    if (tail) buffer += tail
    if (terminal === null && buffer.trim()) {
      for (const evt of parseSseBlocks(buffer)) {
        terminal = handleSseEvent(evt, baseContent, generatedRef)
        if (terminal !== null) break
      }
    }
    if (terminal === 'error') {
      // 错误已在 handleSseEvent 中 toast，不再重复提示
    } else if (!generatedRef.value) {
      toast.warning('未收到生成内容')
    } else {
      toast.success('生成完成')
      emit('generated', generatedRef.value)
    }
  } catch (e: unknown) {
    const err = e as { name?: string; message?: string }
    if (err?.name === 'AbortError') {
      toast.info('已取消生成')
    } else {
      toast.error(err?.message || '生成失败')
    }
  } finally {
    isGenerating.value = false
    generateAbort = null
    // 清理超时定时器与合并信号监听器，避免内存泄漏
    combineCleanup()
    timeoutCleanup()
  }
}

const autopilotRunning = ref(false)
const autopilotProgress = ref<{ current: number; total: number; words: number } | null>(null)
let autopilotTimer: ReturnType<typeof setInterval> | null = null
let autopilotSessionId: string | null = null

async function toggleAutopilot() {
  if (autopilotRunning.value) {
    if (autopilotSessionId) {
      try {
        await cancelSession(autopilotSessionId)
      } catch {
        /* 忽略取消失败 */
      }
    }
    stopAutopilotPolling()
    toast.info('已停止自动驾驶')
    return
  }
  const novelId = route.params.novelId as string
  if (!novelId) {
    toast.error('未识别到小说 ID，无法启动自动驾驶')
    return
  }
  try {
    const session = await createSession({ novel_id: novelId })
    autopilotSessionId = session.session_id
    await startSession(session.session_id)
    autopilotRunning.value = true
    autopilotProgress.value = {
      current: session.current_chapter_index,
      total: session.target_chapters,
      words: session.total_words_generated,
    }
    toast.success('自动驾驶已启动')
    startAutopilotPolling()
  } catch (e: unknown) {
    const err = e as { message?: string }
    toast.error(err?.message || '启动自动驾驶失败')
    autopilotSessionId = null
    autopilotRunning.value = false
  }
}

function startAutopilotPolling() {
  autopilotTimer = setInterval(async () => {
    if (!autopilotSessionId) return
    try {
      const s = await getSession(autopilotSessionId)
      autopilotProgress.value = {
        current: s.current_chapter_index,
        total: s.target_chapters,
        words: s.total_words_generated,
      }
      if (s.state === 'completed' || s.state === 'success') {
        toast.success(`自动驾驶完成，共生成 ${s.total_chapters_completed} 章`)
        stopAutopilotPolling()
      } else if (s.state === 'failed' || s.state === 'error') {
        toast.error(s.error || '自动驾驶失败')
        stopAutopilotPolling()
      }
    } catch (e: unknown) {
      const err = e as { message?: string }
      toast.error(err?.message || '轮询会话状态失败')
      stopAutopilotPolling()
    }
  }, 3000)
}

function stopAutopilotPolling() {
  if (autopilotTimer) {
    clearInterval(autopilotTimer)
    autopilotTimer = null
  }
  autopilotRunning.value = false
  autopilotSessionId = null
}

onBeforeUnmount(() => {
  if (generateAbort) {
    generateAbort.abort()
    generateAbort = null
  }
  if (autopilotTimer) {
    clearInterval(autopilotTimer)
    autopilotTimer = null
  }
})

defineExpose({
  runQualityAudit: () => qualityPanelRef.value?.runAudit(),
})
</script>

<style scoped>
.ai-console {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--xy-surface-1);
}

.console-header {
  flex-shrink: 0;
  padding: 14px 16px 12px;
  border-bottom: 1px solid var(--xy-border-1);
  background: linear-gradient(180deg, var(--xy-surface-2) 0%, var(--xy-surface-1) 100%);
}

.console-title {
  font-family: var(--xy-font-display);
  font-size: 15px;
  font-weight: 600;
  color: var(--xy-text-1);
  margin-bottom: 12px;
  display: block;
  letter-spacing: 0.01em;
}

.console-tabs {
  display: flex;
  gap: 3px;
  padding: 3px;
  background: var(--xy-surface-2);
  border-radius: var(--xy-radius-lg);
  border: 1px solid var(--xy-border-1);
}

.tab-btn {
  flex: 1;
  padding: 5px 6px;
  border: none;
  background: transparent;
  color: var(--xy-text-4);
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
  border-radius: var(--xy-radius-md);
  transition: all var(--xy-dur-sm) var(--xy-ease-standard);
  letter-spacing: 0.02em;
}

.tab-btn:hover {
  color: var(--xy-text-2);
}

.tab-btn.active {
  background: linear-gradient(135deg, var(--xy-brand-500), var(--xy-brand-600));
  color: var(--xy-brand-starlight);
  font-weight: 600;
  box-shadow: 0 2px 8px rgba(124, 108, 191, 0.3);
}

.console-body {
  flex: 1;
  overflow-y: auto;
}

.tab-content {
  padding: 18px 16px;
}

.tab-content-full {
  height: 100%;
  overflow: hidden;
}

.generate-section {
  margin-bottom: 22px;
}

.generate-section:last-of-type {
  margin-bottom: 0;
}

.section-title {
  font-size: 11px;
  font-weight: 600;
  color: var(--xy-text-4);
  margin-bottom: 10px;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.mode-selector {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.mode-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 5px;
  padding: 12px 8px;
  border: 1px solid var(--xy-border-1);
  border-radius: var(--xy-radius-lg);
  background: var(--xy-surface-2);
  color: var(--xy-text-3);
  font-size: 11px;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--xy-dur-sm) var(--xy-ease-standard);
}

.mode-btn:hover {
  border-color: var(--xy-brand-300);
  background: var(--xy-surface-hover);
  color: var(--xy-text-2);
}

.mode-btn.active {
  border-color: var(--xy-brand-500);
  background: color-mix(in srgb, var(--xy-brand-500) 10%, transparent);
  color: var(--xy-brand-starlight);
  box-shadow: inset 0 0 0 1px color-mix(in srgb, var(--xy-brand-500) 30%, transparent);
}

.mode-icon {
  width: 18px;
  height: 18px;
}

.param-item {
  margin-bottom: 14px;
}

.param-item label {
  display: block;
  font-size: 12px;
  color: var(--xy-text-3);
  margin-bottom: 6px;
  font-weight: 500;
}

.guard-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.guard-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 12px;
  background: var(--xy-surface-2);
  border-radius: var(--xy-radius-md);
  font-size: 12px;
  color: var(--xy-text-2);
  border: 1px solid transparent;
  transition: border-color var(--xy-dur-sm) var(--xy-ease-standard);
}

.guard-item:hover {
  border-color: var(--xy-border-2);
}

.guard-name {
  font-size: 12px;
  font-weight: 500;
}

.generate-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 24px;
}

.generate-btn,
.auto-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 16px;
  border: none;
  border-radius: var(--xy-radius-lg);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all var(--xy-dur-sm) var(--xy-ease-standard);
  letter-spacing: 0.02em;
}

.generate-btn {
  background: linear-gradient(135deg, var(--xy-brand-500), var(--xy-brand-600));
  color: var(--xy-brand-starlight);
  box-shadow: 0 4px 14px rgba(124, 108, 191, 0.3);
}

.generate-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(124, 108, 191, 0.4);
  filter: brightness(1.05);
}

.generate-btn:active {
  transform: translateY(0);
}

.auto-btn {
  background: var(--xy-surface-2);
  color: var(--xy-text-2);
  border: 1px solid var(--xy-border-1);
  font-weight: 500;
}

.auto-btn:hover {
  background: var(--xy-surface-hover);
  border-color: var(--xy-border-2);
  color: var(--xy-text-1);
}

.btn-icon {
  width: 16px;
  height: 16px;
}

.history-empty {
  text-align: center;
  padding: 48px 20px;
  color: var(--xy-text-4);
  font-size: 13px;
}

.generate-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
  transform: none;
  box-shadow: 0 4px 14px rgba(124, 108, 191, 0.2);
}

.auto-btn.running {
  border-color: var(--xy-brand-500);
  color: var(--xy-brand-starlight);
  background: color-mix(in srgb, var(--xy-brand-500) 10%, transparent);
}

.autopilot-progress {
  margin-top: 4px;
  padding: 8px 12px;
  background: var(--xy-surface-2);
  border: 1px solid var(--xy-border-1);
  border-radius: var(--xy-radius-md);
  font-size: 11px;
  color: var(--xy-text-3);
  text-align: center;
  letter-spacing: 0.02em;
}
</style>
