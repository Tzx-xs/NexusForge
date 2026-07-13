<template>
  <div class="module-panel new-novel-panel">
    <div class="panel-inner">
      <div class="form-card">
        <div class="form-section">
          <h2 class="section-title">基础信息</h2>

          <!-- 小说标题 -->
          <div class="form-group">
            <label class="form-label">
              小说标题 <span class="required">*</span>
            </label>
            <input
              v-model="form.title"
              class="form-input"
              :class="{ error: errors.title }"
              type="text"
              placeholder="输入小说标题，如《渊海纪元》"
              maxlength="50"
              @blur="validateField('title')"
            />
            <p v-if="errors.title" class="error-text">{{ errors.title }}</p>
            <p class="char-count">{{ form.title.length }}/50</p>
          </div>

          <!-- 故事简介 -->
          <div class="form-group">
            <label class="form-label">
              故事简介 <span class="required">*</span>
            </label>
            <textarea
              v-model="form.synopsis"
              class="form-input"
              :class="{ error: errors.synopsis }"
              rows="5"
              placeholder="用一段话描述你的故事核心设定与主线剧情..."
              maxlength="500"
              @blur="validateField('synopsis')"
            />
            <p v-if="errors.synopsis" class="error-text">{{ errors.synopsis }}</p>
            <p class="char-count">{{ form.synopsis.length }}/500</p>
          </div>

          <!-- 类型与视角 -->
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">
                类型分类 <span class="required">*</span>
              </label>
              <select
                v-model="form.genre"
                class="form-input"
                :class="{ error: errors.genre }"
                @blur="validateField('genre')"
              >
                <option value="">请选择类型</option>
                <option v-for="g in genres" :key="g" :value="g">{{ g }}</option>
              </select>
              <p v-if="errors.genre" class="error-text">{{ errors.genre }}</p>
            </div>
            <div class="form-group">
              <label class="form-label">写作视角</label>
              <select v-model="form.perspective" class="form-input">
                <option v-for="p in perspectives" :key="p.value" :value="p.value">{{ p.label }}</option>
              </select>
            </div>
          </div>

          <!-- 风格标签 -->
          <div class="form-group">
            <label class="form-label">
              风格标签 <span class="required">*</span>
              <span class="label-hint">至少选择 1 个</span>
            </label>
            <div class="tag-group">
              <span
                v-for="tag in styleTags"
                :key="tag"
                class="tag"
                :class="{ selected: form.tags.includes(tag) }"
                @click="toggleTag(tag)"
              >
                {{ tag }}
              </span>
            </div>
            <p v-if="errors.tags" class="error-text">{{ errors.tags }}</p>
          </div>
        </div>

        <div class="form-divider"/>

        <!-- 高级设置 -->
        <details class="advanced-settings">
          <summary>
            <ChevronRight class="advanced-icon"/>
            高级设置
          </summary>
          <div class="advanced-content">
            <div class="form-row">
              <div class="form-group">
                <label class="form-label-sm">目标章数</label>
                <input v-model.number="form.targetChapters" class="form-input" type="number" min="10" max="1000"/>
              </div>
              <div class="form-group">
                <label class="form-label-sm">每章目标字数</label>
                <input v-model.number="form.targetWords" class="form-input" type="number" min="500" max="10000" step="500"/>
              </div>
            </div>
            <div class="form-row">
              <div class="form-group">
                <label class="form-label-sm">基调</label>
                <select v-model="form.tone" class="form-input">
                  <option v-for="t in tones" :key="t" :value="t">{{ t }}</option>
                </select>
              </div>
              <div class="form-group">
                <label class="form-label-sm">篇幅</label>
                <select v-model="form.length" class="form-input">
                  <option v-for="l in lengths" :key="l" :value="l">{{ l }}</option>
                </select>
              </div>
            </div>
          </div>
        </details>

        <!-- 提交按钮 -->
        <div class="form-actions">
          <button class="btn-primary" :disabled="isSubmitting" @click="submit">
            <Plus class="icon-14 btn-plus-icon"/>
            {{ isSubmitting ? '创建中…' : '创建小说' }}
          </button>
          <button class="btn-ghost" @click="importOutline">
            导入大纲文件
          </button>
        </div>

        <!-- 隐藏大纲导入输入 -->
        <input
          ref="outlineInputRef"
          type="file"
          accept=".md,.txt"
          class="outline-input"
          @change="onOutlineSelected"
        />

        <!-- 验证汇总 -->
        <div v-if="showValidationError" class="validation-summary">
          请完成所有必填项后再提交
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useMessage } from 'naive-ui'
import { useNovelStore } from '@/stores/novel'
import { Plus, ChevronRight } from '@vicons/tabler'

const message = useMessage()
const router = useRouter()
const novelStore = useNovelStore()

const genres = ['玄幻', '都市', '科幻', '武侠', '历史', '言情', '悬疑', '奇幻']
const perspectives = [
  { value: 'third', label: '第三人称' },
  { value: 'first', label: '第一人称' },
  { value: 'limited', label: '限知视角' },
]
const styleTags = ['热血', '轻松', '深沉', '悬疑', '甜宠', '黑暗', '史诗', '搞笑', '治愈', '烧脑']
const tones = ['史诗', '轻松', '黑暗', '浪漫']
const lengths = ['长篇 (100万字+)', '中篇 (30-100万字)', '短篇 (<30万字)']

const form = reactive({
  title: '',
  synopsis: '',
  genre: '',
  perspective: 'third',
  tags: [] as string[],
  targetChapters: 100,
  targetWords: 2500,
  tone: '史诗',
  length: '长篇 (100万字+)',
})

const errors = reactive<Record<string, string>>({})
const showValidationError = ref(false)
let validationTimer: ReturnType<typeof setTimeout> | null = null

function validateField(field: string): boolean {
  delete errors[field]
  switch (field) {
    case 'title': {
      const t = form.title.trim()
      if (t.length > 0 && (t.length < 2 || t.length > 50)) {
        errors.title = '请输入小说标题（2-50字）'
        return false
      }
      break
    }
    case 'synopsis': {
      const s = form.synopsis.trim()
      if (s.length > 0 && (s.length < 20 || s.length > 500)) {
        errors.synopsis = '请输入故事简介（20-500字）'
        return false
      }
      break
    }
    case 'genre':
      if (!form.genre) {
        errors.genre = '请选择小说类型'
        return false
      }
      break
  }
  return true
}

function toggleTag(tag: string) {
  const idx = form.tags.indexOf(tag)
  if (idx >= 0) form.tags.splice(idx, 1)
  else form.tags.push(tag)
  delete errors.tags
}

const isSubmitting = ref(false)
const outlineInputRef = ref<HTMLInputElement>()

async function submit() {
  const v1 = form.title.trim().length >= 2 && form.title.trim().length <= 50
  const v2 = form.synopsis.trim().length >= 20 && form.synopsis.trim().length <= 500
  const v3 = !!form.genre
  const v4 = form.tags.length > 0

  if (!v1) errors.title = '请输入小说标题（2-50字）'
  if (!v2) errors.synopsis = '请输入故事简介（20-500字）'
  if (!v3) errors.genre = '请选择小说类型'
  if (!v4) errors.tags = '请至少选择1个风格标签'

  if (!(v1 && v2 && v3 && v4)) {
    showValidationError.value = true
    if (validationTimer) clearTimeout(validationTimer)
    validationTimer = setTimeout(() => { showValidationError.value = false }, 4000)
    return
  }

  isSubmitting.value = true
  try {
    const result = await novelStore.createNovel(
      {
        title: form.title.trim(),
        premise: form.synopsis.trim(),
        genre: form.genre,
        target_chapters: form.targetChapters,
        style_tags: form.tags,
        perspective: form.perspective,
      },
      { _silent: true }
    )
    message.success('小说创建成功！')
    router.push(`/workspace/${result.id}/writing/1`)
  } catch (e) {
    const errMsg = e instanceof Error ? e.message : '小说创建失败，请重试'
    message.error(errMsg)
  } finally {
    isSubmitting.value = false
  }
}

onUnmounted(() => {
  if (validationTimer) clearTimeout(validationTimer)
})

function importOutline() {
  outlineInputRef.value?.click()
}

function onOutlineSelected(e: Event) {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  if (!file) return
  const reader = new FileReader()
  reader.onload = () => {
    const text = String(reader.result || '')
    const lines = text.split(/\r?\n/).filter(Boolean)
    const firstLine = lines[0] || ''
    if (firstLine.startsWith('#') && !form.title) {
      form.title = firstLine.replace(/^#+\s*/, '').trim()
    }
    if (!form.synopsis && lines.length > 1) {
      form.synopsis = lines.slice(1).join('\n').trim().slice(0, 500)
    }
    message.success('大纲已导入')
  }
  reader.onerror = () => {
    message.error('大纲文件读取失败，请重试')
  }
  reader.readAsText(file)
  target.value = ''
}
</script>

<style scoped>
.new-novel-panel {
  animation: xy-fade-in var(--xy-dur-md) var(--xy-ease-standard);
}

.panel-inner {
  max-width: 680px;
  margin: 0 auto;
  padding: 40px 28px 48px;
}

/* Form Card */
.form-card {
  background: var(--xy-surface-1);
  border: 1px solid var(--xy-border-1);
  border-radius: var(--xy-radius-xl, 14px);
  padding: 32px;
}

.form-section {
  margin-bottom: 8px;
}

.section-title {
  font-family: var(--xy-font-display);
  font-size: 18px;
  font-weight: 500;
  color: var(--xy-text-1);
  letter-spacing: 0.01em;
  margin: 0 0 24px;
}

.form-divider {
  height: 1px;
  background: var(--xy-border-1);
  margin: 24px 0;
}

.form-group {
  margin-bottom: 24px;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-bottom: 24px;
}

.form-row .form-group {
  margin-bottom: 0;
}

.form-label {
  display: block;
  font-size: 12px;
  font-weight: 500;
  color: var(--xy-text-2);
  margin-bottom: 8px;
  letter-spacing: 0.01em;
}

.form-label-sm {
  display: block;
  font-size: 11px;
  color: var(--xy-text-3);
  margin-bottom: 6px;
}

.required {
  color: var(--xy-danger);
}

.label-hint {
  font-weight: 400;
  color: var(--xy-text-4);
  font-size: 11px;
  margin-left: 4px;
}

.form-input {
  background: var(--xy-bg-page);
  border: 1px solid var(--xy-border-1);
  border-radius: var(--xy-radius-md, 8px);
  color: var(--xy-text-1);
  padding: 10px 14px;
  font-size: 14px;
  width: 100%;
  transition: border-color var(--xy-dur-sm), box-shadow var(--xy-dur-sm);
  outline: none;
  font-family: inherit;
}

.form-input:focus {
  border-color: var(--xy-border-focus);
  box-shadow: var(--xy-shadow-focus-ring);
}

.form-input.error {
  border-color: var(--xy-border-error);
}

.form-input::placeholder {
  color: var(--xy-text-4);
}

select.form-input {
  appearance: none;
  cursor: pointer;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath d='M2 4l4 4 4-4' fill='none' stroke='%237c778a' stroke-width='1.5' stroke-linecap='round'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 12px center;
  padding-right: 30px;
}

textarea.form-input {
  resize: vertical;
  min-height: 120px;
  line-height: 1.6;
}

.error-text {
  font-size: 11px;
  color: var(--xy-danger);
  margin-top: 6px;
}

.char-count {
  font-size: 11px;
  color: var(--xy-text-4);
  margin-top: 6px;
  text-align: right;
}

.tag-group {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag {
  display: inline-flex;
  align-items: center;
  padding: 5px 12px;
  border-radius: var(--xy-radius-full, 9999px);
  font-size: 12px;
  background: var(--xy-bg-page);
  color: var(--xy-text-2);
  border: 1px solid var(--xy-border-1);
  cursor: pointer;
  transition: all var(--xy-dur-sm);
  user-select: none;
}

.tag:hover {
  background: var(--xy-surface-hover);
  color: var(--xy-text-1);
  border-color: var(--xy-border-2);
}

.tag.selected {
  background: var(--xy-accent-soft);
  color: var(--xy-accent);
  border-color: rgba(212, 168, 83, 0.35);
}

.advanced-settings {
  margin-bottom: 28px;
}

.advanced-settings summary {
  padding: 10px 0;
  font-size: 13px;
  color: var(--xy-text-2);
  cursor: pointer;
  user-select: none;
  list-style: none;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}

.advanced-settings summary::-webkit-details-marker {
  display: none;
}

.advanced-icon {
  width: 13px;
  height: 13px;
  transition: transform var(--xy-dur-sm);
}

.icon-12 {
  width: 12px;
  height: 12px;
}

.icon-14 {
  width: 14px;
  height: 14px;
}

.btn-plus-icon :deep(path),
.btn-plus-icon :deep(g) {
  stroke-width: 2.5;
}

.advanced-settings[open] .advanced-icon {
  transform: rotate(90deg);
}

.advanced-content {
  padding: 20px 0 4px;
}

.form-actions {
  display: flex;
  align-items: center;
  gap: 14px;
  padding-top: 8px;
}

.btn-primary {
  background: linear-gradient(135deg, #c99a42, #d4a853 50%, #e0bd6e);
  color: var(--xy-text-inverse);
  border: none;
  border-radius: var(--xy-radius-md, 8px);
  padding: 10px 24px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--xy-dur-sm);
  display: inline-flex;
  align-items: center;
  gap: 7px;
}

.btn-primary:hover {
  filter: brightness(1.08);
  transform: translateY(-1px);
  box-shadow: 0 6px 20px rgba(212, 168, 83, 0.22);
}

.btn-primary:active {
  transform: translateY(0);
  filter: brightness(1);
}

.btn-primary:disabled {
  opacity: 0.7;
  cursor: not-allowed;
  transform: none;
}

.outline-input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
  pointer-events: none;
}

.btn-ghost {
  background: transparent;
  color: var(--xy-text-2);
  border: 1px solid var(--xy-border-1);
  border-radius: var(--xy-radius-md, 8px);
  padding: 10px 24px;
  font-size: 14px;
  cursor: pointer;
  transition: all var(--xy-dur-sm);
}

.btn-ghost:hover {
  background: var(--xy-surface-hover);
  color: var(--xy-text-1);
  border-color: var(--xy-border-2);
}

.validation-summary {
  margin-top: 18px;
  padding: 12px 16px;
  border-radius: var(--xy-radius-md, 8px);
  background: var(--xy-danger-bg);
  border: 1px solid rgba(242, 133, 133, 0.18);
  font-size: 13px;
  color: var(--xy-danger);
}

@media (max-width: 640px) {
  .panel-inner {
    padding: 24px 20px 32px;
  }
  .form-card {
    padding: 24px;
  }
  .form-row {
    grid-template-columns: 1fr;
  }
}
</style>