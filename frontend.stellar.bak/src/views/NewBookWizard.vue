<template>
  <div class="wizard-overlay">
    <div class="wizard-card">
      <div class="wizard-header">
        <div class="wizard-brand">
          <Star class="brand-icon" />
          <span class="brand-text">新建你的小说</span>
        </div>
        <button class="close-btn" aria-label="关闭" @click="closeWizard">
          <X class="close-icon" />
        </button>
      </div>

      <div class="steps-indicator">
        <div
          v-for="(step, index) in steps"
          :key="step.id"
          class="step-item"
          :class="{
            'step-completed': currentStep > index,
            'step-current': currentStep === index,
            'step-upcoming': currentStep < index,
          }"
        >
          <div class="step-dot">
            <Check v-if="currentStep > index" class="check-icon" />
            <span v-else-if="currentStep === index" class="current-dot"></span>
          </div>
          <span class="step-label">{{ step.label }}</span>
          <div v-if="index < steps.length - 1" class="step-connector"></div>
        </div>
      </div>

      <div class="wizard-body">
        <div class="step-content">
          <h2 class="step-title">{{ steps[currentStep].title }}</h2>
          <p class="step-desc">{{ steps[currentStep].description }}</p>

          <div v-if="currentStep === 0" class="form-grid">
            <div class="form-item">
              <label class="form-label">小说名称</label>
              <input
                v-model="formData.title"
                type="text"
                class="form-input"
                :class="{ 'input-error': errors.title }"
                placeholder="请输入小说名称"
              />
              <span v-if="errors.title" class="error-text">{{ errors.title }}</span>
            </div>
            <div class="form-item">
              <label class="form-label">小说类型</label>
              <select v-model="formData.genre" class="form-select">
                <option>玄幻</option>
                <option>都市</option>
                <option>科幻</option>
                <option>仙侠</option>
                <option>悬疑</option>
              </select>
            </div>
            <div class="form-item">
              <label class="form-label">作者笔名</label>
              <input
                v-model="formData.author"
                type="text"
                class="form-input"
                placeholder="请输入作者笔名"
              />
            </div>
            <div class="form-item">
              <label class="form-label">目标字数</label>
              <select v-model="formData.targetWordCount" class="form-select">
                <option>长篇 (100万字+)</option>
                <option>中篇 (30-100万字)</option>
                <option>短篇 (10-30万字)</option>
              </select>
            </div>
            <div class="form-item form-item-full">
              <label class="form-label">故事简介</label>
              <textarea
                v-model="formData.premise"
                class="form-textarea"
                :class="{ 'input-error': errors.premise }"
                rows="4"
                placeholder="简要描述你的故事构想..."
              ></textarea>
              <span v-if="errors.premise" class="error-text">{{ errors.premise }}</span>
            </div>
          </div>

          <div v-if="currentStep === 1" class="form-grid">
            <div class="form-item">
              <label class="form-label">时代背景</label>
              <select v-model="formData.era" class="form-select">
                <option>架空古代</option>
                <option>现代都市</option>
                <option>未来科幻</option>
                <option>仙侠修真</option>
                <option>末日废土</option>
                <option>中世纪奇幻</option>
              </select>
            </div>
            <div class="form-item">
              <label class="form-label">世界类型</label>
              <select v-model="formData.worldType" class="form-select">
                <option>单一世界</option>
                <option>多元宇宙</option>
                <option>平行世界</option>
                <option>位面世界</option>
              </select>
            </div>
            <div class="form-item form-item-full">
              <label class="form-label">力量体系</label>
              <textarea
                v-model="formData.powerSystem"
                class="form-textarea"
                rows="3"
                placeholder="描述这个世界的力量体系，如修炼等级、魔法系统、科技水平等..."
              ></textarea>
            </div>
            <div class="form-item form-item-full">
              <label class="form-label">社会结构</label>
              <textarea
                v-model="formData.socialStructure"
                class="form-textarea"
                rows="3"
                placeholder="描述世界的社会结构，如势力分布、阶级制度、政治体系等..."
              ></textarea>
            </div>
            <div class="form-item form-item-full">
              <label class="form-label">重要地点</label>
              <textarea
                v-model="formData.locations"
                class="form-textarea"
                rows="3"
                placeholder="列出故事中的重要地点及其特点..."
              ></textarea>
            </div>
          </div>

          <div v-if="currentStep === 2" class="form-grid">
            <div class="form-item">
              <label class="form-label">主角姓名</label>
              <input
                v-model="formData.protagonistName"
                type="text"
                class="form-input"
                placeholder="请输入主角姓名"
              />
            </div>
            <div class="form-item">
              <label class="form-label">主角性格</label>
              <select v-model="formData.protagonistPersonality" class="form-select">
                <option>热血坚毅</option>
                <option>冷静睿智</option>
                <option>腹黑算计</option>
                <option>乐观开朗</option>
                <option>孤傲高冷</option>
              </select>
            </div>
            <div class="form-item form-item-full">
              <label class="form-label">主角背景</label>
              <textarea
                v-model="formData.protagonistBackground"
                class="form-textarea"
                rows="3"
                placeholder="描述主角的出身、经历和目标..."
              ></textarea>
            </div>
            <div class="form-item form-item-full">
              <label class="form-label">重要配角</label>
              <textarea
                v-model="formData.supportingCharacters"
                class="form-textarea"
                rows="4"
                placeholder="列出重要配角及其与主角的关系..."
              ></textarea>
            </div>
          </div>

          <div v-if="currentStep === 3" class="outline-preview">
            <div class="outline-card">
              <div class="outline-header">
                <Bulb class="outline-icon" />
                <span class="outline-title">AI 大纲生成预览</span>
              </div>
              <div class="outline-body">
                <div class="outline-item">
                  <span class="outline-volume">第一卷</span>
                  <span class="outline-volume-title">初入江湖</span>
                </div>
                <div class="outline-item">
                  <span class="outline-volume">第二卷</span>
                  <span class="outline-volume-title">风云际会</span>
                </div>
                <div class="outline-item">
                  <span class="outline-volume">第三卷</span>
                  <span class="outline-volume-title">巅峰之路</span>
                </div>
                <div class="outline-item">
                  <span class="outline-volume">第四卷</span>
                  <span class="outline-volume-title">终极对决</span>
                </div>
              </div>
            </div>
            <p class="generate-hint">点击「创建小说」后，AI 将基于你填写的信息自动生成详细大纲</p>
          </div>
        </div>
      </div>

      <div class="wizard-footer">
        <button v-if="currentStep < steps.length - 1" class="btn-skip" @click="skipWizard">
          跳过向导
        </button>
        <div v-else></div>
        <div class="footer-buttons">
          <button class="btn-ghost" :disabled="currentStep === 0" @click="prevStep">
            <ChevronLeft class="btn-icon" />
            上一步
          </button>
          <button class="btn-primary" :disabled="isCreating" @click="nextStep">
            {{
              isCreating ? '创建中...' : currentStep === steps.length - 1 ? '创建小说' : '下一步'
            }}
            <ChevronRight v-if="currentStep < steps.length - 1" class="btn-icon" />
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { Check, ChevronRight, ChevronLeft, Star, X, Bulb } from '@vicons/tabler'
import { useNovelStore } from '@/stores/novel'
import { toast } from '@/utils/toast'

const router = useRouter()
const route = useRoute()
const novelStore = useNovelStore()
const currentStep = ref(0)
const isCreating = ref(false)
const errors = ref<Record<string, string>>({})

const formData = reactive({
  title: '',
  genre: '玄幻',
  author: '',
  targetWordCount: '长篇 (100万字+)',
  premise: '',
  era: '架空古代',
  worldType: '单一世界',
  powerSystem: '',
  socialStructure: '',
  locations: '',
  protagonistName: '',
  protagonistPersonality: '热血坚毅',
  protagonistBackground: '',
  supportingCharacters: '',
})

onMounted(() => {
  const query = route.query
  if (query.title != null && query.title !== '') {
    formData.title = String(query.title)
  }
  if (query.genre != null && query.genre !== '') {
    formData.genre = String(query.genre)
  }
  if (query.premise != null && query.premise !== '') {
    formData.premise = String(query.premise)
  }
  if (query.target_chapters != null && query.target_chapters !== '') {
    const chapters = Number(query.target_chapters)
    if (!Number.isNaN(chapters)) {
      if (chapters >= 150) {
        formData.targetWordCount = '长篇 (100万字+)'
      } else if (chapters >= 80) {
        formData.targetWordCount = '中篇 (30-100万字)'
      } else {
        formData.targetWordCount = '短篇 (10-30万字)'
      }
    }
  }
})

const steps = [
  {
    id: 'basic',
    label: '基础信息',
    title: '基础信息',
    description: '填写小说的基本信息，让我们开始你的创作之旅',
  },
  {
    id: 'world',
    label: '世界观设定',
    title: '世界观设定',
    description: '请设定你的故事世界，AI 将基于此生成更贴合的内容',
  },
  {
    id: 'characters',
    label: '人物设定',
    title: '人物设定',
    description: '塑造你的故事角色，让他们在故事中鲜活起来',
  },
  {
    id: 'outline',
    label: '大纲生成',
    title: '大纲生成',
    description: '确认所有设定，AI 将为你生成完整的故事大纲',
  },
]

const prevStep = () => {
  if (currentStep.value > 0) {
    currentStep.value--
    errors.value = {}
  }
}

function validateStep(step: number): boolean {
  errors.value = {}

  if (step === 0) {
    if (!formData.title.trim()) {
      errors.value.title = '请输入小说名称'
    }
    if (!formData.premise.trim()) {
      errors.value.premise = '请输入故事简介'
    }
  }

  return Object.keys(errors.value).length === 0
}

const nextStep = async () => {
  if (!validateStep(currentStep.value)) {
    return
  }

  if (currentStep.value < steps.length - 1) {
    currentStep.value++
  } else {
    await createNovel()
  }
}

const createNovel = async () => {
  isCreating.value = true
  try {
    const targetChapters = formData.targetWordCount.includes('长篇')
      ? 200
      : formData.targetWordCount.includes('中篇')
        ? 100
        : 50
    const styleTags = (() => {
      const raw = route.query.style_tags || route.query.style || ''
      if (!raw) return undefined
      if (Array.isArray(raw)) return raw.map(String).filter(Boolean)
      return String(raw)
        .split(',')
        .map((s) => s.trim())
        .filter(Boolean)
    })()
    const perspective = route.query.perspective ? String(route.query.perspective) : undefined
    const result = await novelStore.createNovel(
      {
        title: formData.title || '新小说',
        premise: formData.premise,
        genre: formData.genre,
        target_chapters: targetChapters,
        style_tags: styleTags,
        perspective,
      },
      { _silent: true }
    )
    const newNovelId = result.id
    if (!newNovelId) {
      throw new Error('创建小说失败：未返回小说 ID')
    }
    // 保留世界观/人物等扩展字段到 localStorage，BiblePage 会检测并提示导入
    const draftKey = `xy-novel-draft-${newNovelId}`
    const draftData = {
      era: formData.era,
      worldType: formData.worldType,
      powerSystem: formData.powerSystem,
      socialStructure: formData.socialStructure,
      locations: formData.locations,
      protagonistName: formData.protagonistName,
      protagonistPersonality: formData.protagonistPersonality,
      protagonistBackground: formData.protagonistBackground,
      supportingCharacters: formData.supportingCharacters,
      style: String(route.query.style || ''),
      perspective: String(route.query.perspective || ''),
      updateFreq: String(route.query.update_freq || ''),
      audience: String(route.query.audience || ''),
      aiMode: String(route.query.ai_mode || ''),
      targetReader: String(route.query.target_reader || ''),
    }
    localStorage.setItem(draftKey, JSON.stringify(draftData))
    toast.success('小说创建成功，正在跳转...')
    router.push(`/workspace/${newNovelId}/writing/1`)
  } catch (e) {
    console.error('Failed to create novel:', e)
    const err = e as { message?: string }
    // 创建失败时不跳转到硬编码工作区，留在向导页提示错误（审查报告 2.7）
    toast.error(err?.message || '创建小说失败，请重试')
  } finally {
    isCreating.value = false
  }
}

const skipWizard = async () => {
  isCreating.value = true
  try {
    const result = await novelStore.createNovel(
      {
        title: '未命名小说',
        premise: '待补充',
        genre: '玄幻',
        target_chapters: 50,
      },
      { _silent: true }
    )
    const newNovelId = result.id || '1'
    // 跳过向导不写 localStorage 草稿（因为没填扩展字段）
    router.push(`/workspace/${newNovelId}/writing/1`)
  } catch (e) {
    console.error('Failed to skip wizard:', e)
    router.push('/')
  } finally {
    isCreating.value = false
  }
}

const closeWizard = () => {
  router.push('/')
}
</script>

<style scoped>
.wizard-overlay {
  position: fixed;
  inset: 0;
  z-index: var(--xy-z-modal-backdrop);
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, 0.72);
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
  animation: fade-in var(--xy-dur-lg) var(--xy-ease-enter) both;
}

@keyframes fade-in {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.wizard-card {
  width: 720px;
  max-width: calc(100vw - 48px);
  max-height: calc(100vh - 80px);
  display: flex;
  flex-direction: column;
  background: var(--xy-surface-1);
  border-radius: var(--xy-radius-xl);
  box-shadow: var(--xy-shadow-modal);
  border: 1px solid var(--xy-border-1);
  animation: card-enter var(--xy-dur-lg) var(--xy-ease-enter) both;
  overflow: hidden;
}

@keyframes card-enter {
  from {
    opacity: 0;
    transform: scale(0.96) translateY(10px);
  }
  to {
    opacity: 1;
    transform: scale(1) translateY(0);
  }
}

.wizard-header {
  height: 52px;
  min-height: 52px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--xy-space-6);
  border-bottom: 1px solid var(--xy-border-1);
  background: var(--xy-surface-1);
}

.wizard-brand {
  display: flex;
  align-items: center;
  gap: var(--xy-space-2);
}

.brand-icon {
  width: 18px;
  height: 18px;
  color: var(--xy-brand-500);
}

.brand-text {
  font-size: var(--xy-fs-md);
  font-weight: var(--xy-fw-sb);
  color: var(--xy-text-1);
}

.close-btn {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: 1px solid transparent;
  border-radius: var(--xy-radius-md);
  color: var(--xy-text-3);
  cursor: pointer;
  transition:
    color var(--xy-dur-sm) var(--xy-ease-standard),
    background var(--xy-dur-sm) var(--xy-ease-standard);
}

.close-btn:hover {
  color: var(--xy-text-1);
  background: var(--xy-surface-hover);
}

.close-icon {
  width: 16px;
  height: 16px;
}

.steps-indicator {
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: var(--xy-space-6) var(--xy-space-8) var(--xy-space-4);
  position: relative;
}

.step-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  position: relative;
  flex: 1;
  max-width: 140px;
}

.step-dot {
  width: 28px;
  height: 28px;
  border-radius: var(--xy-radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  z-index: 2;
  transition: all var(--xy-dur-md) var(--xy-ease-standard);
}

.step-completed .step-dot {
  background: var(--xy-success);
}

.step-current .step-dot {
  background: var(--xy-brand-100);
  border: 2px solid var(--xy-brand-500);
  box-shadow: 0 0 0 4px rgba(124, 108, 191, 0.12);
}

.step-upcoming .step-dot {
  background: transparent;
  border: 2px solid var(--xy-border-2);
}

.check-icon {
  width: 14px;
  height: 14px;
  color: var(--xy-text-inverse);
}

.current-dot {
  width: 10px;
  height: 10px;
  border-radius: var(--xy-radius-full);
  background: var(--xy-brand-500);
}

.step-label {
  margin-top: var(--xy-space-2);
  font-size: var(--xy-fs-sm);
  font-weight: var(--xy-fw-med);
  white-space: nowrap;
  transition: color var(--xy-dur-md) var(--xy-ease-standard);
}

.step-completed .step-label {
  color: var(--xy-text-2);
}

.step-current .step-label {
  color: var(--xy-text-1);
  font-weight: var(--xy-fw-sb);
}

.step-upcoming .step-label {
  color: var(--xy-text-4);
}

.step-connector {
  position: absolute;
  top: 14px;
  left: calc(50% + 18px);
  width: calc(100% - 36px);
  height: 2px;
  background: var(--xy-border-2);
  z-index: 1;
  transition: background var(--xy-dur-md) var(--xy-ease-standard);
}

.step-completed .step-connector {
  background: var(--xy-success);
}

.wizard-body {
  flex: 1;
  overflow-y: auto;
  padding: var(--xy-space-4) var(--xy-space-8) var(--xy-space-6);
  min-height: 0;
}

.step-content {
  animation: content-fade-in var(--xy-dur-md) var(--xy-ease-enter) both;
}

@keyframes content-fade-in {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.step-title {
  font-size: var(--xy-fs-xl);
  font-weight: var(--xy-fw-bold);
  color: var(--xy-text-1);
  margin: 0 0 var(--xy-space-2) 0;
}

.step-desc {
  font-size: var(--xy-fs-md);
  color: var(--xy-text-3);
  margin: 0 0 var(--xy-space-6) 0;
  line-height: var(--xy-lh-normal);
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: var(--xy-space-4);
}

.form-item {
  display: flex;
  flex-direction: column;
}

.form-item-full {
  grid-column: 1 / -1;
}

.form-label {
  font-size: var(--xy-fs-sm);
  font-weight: var(--xy-fw-med);
  color: var(--xy-text-2);
  margin-bottom: var(--xy-space-2);
}

.form-input,
.form-select,
.form-textarea {
  width: 100%;
  padding: var(--xy-space-3) var(--xy-space-4);
  background: var(--xy-surface-2);
  border: 1px solid var(--xy-border-1);
  border-radius: var(--xy-radius-md);
  color: var(--xy-text-1);
  font-family: var(--xy-font-sans);
  font-size: var(--xy-fs-md);
  line-height: var(--xy-lh-normal);
  box-sizing: border-box;
  transition:
    border-color var(--xy-dur-sm) var(--xy-ease-standard),
    box-shadow var(--xy-dur-sm) var(--xy-ease-standard);
}

.form-input::placeholder,
.form-textarea::placeholder {
  color: var(--xy-text-4);
}

.form-input:hover,
.form-select:hover,
.form-textarea:hover {
  border-color: var(--xy-border-2);
}

.form-input:focus,
.form-select:focus,
.form-textarea:focus {
  outline: none;
  border-color: var(--xy-border-focus);
  box-shadow: var(--xy-shadow-focus-ring);
}

.form-select {
  appearance: none;
  cursor: pointer;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%237d7598' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 12px center;
  padding-right: 36px;
}

.form-textarea {
  resize: vertical;
  min-height: 80px;
}

.input-error {
  border-color: var(--xy-danger) !important;
}

.error-text {
  color: var(--xy-danger);
  font-size: var(--xy-fs-xs);
  margin-top: var(--xy-space-1);
}

.outline-preview {
  display: flex;
  flex-direction: column;
  gap: var(--xy-space-4);
}

.outline-card {
  background: var(--xy-surface-2);
  border: 1px solid var(--xy-border-1);
  border-radius: var(--xy-radius-lg);
  overflow: hidden;
}

.outline-header {
  display: flex;
  align-items: center;
  gap: var(--xy-space-2);
  padding: var(--xy-space-4);
  background: var(--xy-brand-50);
  border-bottom: 1px solid var(--xy-border-1);
}

.outline-icon {
  width: 18px;
  height: 18px;
  color: var(--xy-brand-500);
}

.outline-title {
  font-size: var(--xy-fs-md);
  font-weight: var(--xy-fw-sb);
  color: var(--xy-text-1);
}

.outline-body {
  padding: var(--xy-space-4);
  display: flex;
  flex-direction: column;
  gap: var(--xy-space-3);
}

.outline-item {
  display: flex;
  align-items: center;
  gap: var(--xy-space-3);
  padding: var(--xy-space-3);
  background: var(--xy-surface-1);
  border-radius: var(--xy-radius-md);
  border: 1px solid var(--xy-border-1);
}

.outline-volume {
  font-size: var(--xy-fs-sm);
  font-weight: var(--xy-fw-sb);
  color: var(--xy-brand-500);
  min-width: 50px;
}

.outline-volume-title {
  font-size: var(--xy-fs-md);
  color: var(--xy-text-1);
}

.generate-hint {
  font-size: var(--xy-fs-sm);
  color: var(--xy-text-3);
  text-align: center;
  margin: 0;
}

.wizard-footer {
  height: 64px;
  min-height: 64px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--xy-space-6);
  border-top: 1px solid var(--xy-border-1);
  background: var(--xy-surface-1);
}

.btn-skip {
  background: transparent;
  border: none;
  color: var(--xy-text-3);
  font-size: var(--xy-fs-md);
  font-family: var(--xy-font-sans);
  cursor: pointer;
  padding: var(--xy-space-2) var(--xy-space-3);
  border-radius: var(--xy-radius-md);
  transition: color var(--xy-dur-sm) var(--xy-ease-standard);
}

.btn-skip:hover {
  color: var(--xy-text-1);
}

.footer-buttons {
  display: flex;
  align-items: center;
  gap: var(--xy-space-3);
}

.btn-ghost,
.btn-primary {
  display: inline-flex;
  align-items: center;
  gap: var(--xy-space-2);
  height: 40px;
  padding: 0 var(--xy-space-5);
  border-radius: var(--xy-radius-md);
  font-family: var(--xy-font-sans);
  font-size: var(--xy-fs-md);
  font-weight: var(--xy-fw-sb);
  cursor: pointer;
  transition: all var(--xy-dur-sm) var(--xy-ease-standard);
  border: none;
  white-space: nowrap;
}

.btn-icon {
  width: 16px;
  height: 16px;
}

.btn-ghost {
  background: transparent;
  color: var(--xy-text-2);
  border: 1px solid var(--xy-border-2);
}

.btn-ghost:hover:not(:disabled) {
  color: var(--xy-text-1);
  background: var(--xy-surface-hover);
  border-color: var(--xy-text-3);
}

.btn-ghost:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.btn-primary {
  background: var(--xy-brand-500);
  color: var(--xy-text-inverse);
}

.btn-primary:hover {
  background: var(--xy-brand-400);
  transform: translateY(-1px);
}

.btn-primary:active {
  transform: translateY(0);
}

.btn-primary:focus-visible,
.btn-ghost:focus-visible,
.btn-skip:focus-visible {
  outline: none;
  box-shadow: var(--xy-shadow-focus-ring);
}

@media (prefers-reduced-motion: reduce) {
  .wizard-overlay,
  .wizard-card,
  .step-content,
  .step-dot,
  .step-label,
  .step-connector,
  .btn-primary,
  .btn-ghost {
    animation-duration: 0.01ms !important;
    transition-duration: 0.01ms !important;
  }
}
</style>
