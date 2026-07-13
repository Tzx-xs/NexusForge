<template>
  <div class="settings-page">
    <div class="settings-container">
      <aside class="settings-sidebar">
        <button class="back-home-btn" aria-label="返回工作台" @click="router.push('/')">
          <ArrowLeft class="back-icon" />
          <span>返回工作台</span>
        </button>
        <div class="sidebar-header">
          <Settings class="sidebar-icon" />
          <span class="sidebar-title">设置</span>
        </div>

        <nav class="sidebar-nav">
          <div class="nav-group">
            <div class="nav-group-title">小说设置</div>
            <div
              v-for="item in novelSettingsItems"
              :key="item.key"
              class="nav-item"
              :class="{ active: activeNav === item.key }"
              @click="activeNav = item.key"
            >
              <component :is="item.icon" class="nav-item-icon" />
              <span class="nav-item-text">{{ item.label }}</span>
              <ChevronRight class="nav-item-arrow" />
            </div>
          </div>

          <div class="nav-group">
            <div class="nav-group-title">全局设置</div>
            <div
              v-for="item in globalSettingsItems"
              :key="item.key"
              class="nav-item"
              :class="{ active: activeNav === item.key }"
              @click="activeNav = item.key"
            >
              <component :is="item.icon" class="nav-item-icon" />
              <span class="nav-item-text">{{ item.label }}</span>
              <ChevronRight class="nav-item-arrow" />
            </div>
          </div>
        </nav>
      </aside>

      <main class="settings-main">
        <div class="main-scroll">
          <header class="main-header">
            <h1 class="page-title">{{ currentPageTitle }}</h1>
          </header>

          <div class="main-content">
            <div v-if="activeNav === 'basic'" class="content-section">
              <div class="section-card">
                <div class="section-title">基础信息</div>

                <div class="form-row">
                  <label class="form-label">用户名</label>
                  <div class="form-control">
                    <input
                      v-model="settings.basic.username"
                      type="text"
                      class="form-input"
                      placeholder="请输入用户名"
                    />
                  </div>
                </div>

                <div class="form-row">
                  <label class="form-label">作者笔名</label>
                  <div class="form-control">
                    <input
                      v-model="settings.basic.penName"
                      type="text"
                      class="form-input"
                      placeholder="请输入作者笔名"
                    />
                  </div>
                </div>

                <div class="form-row">
                  <label class="form-label">邮箱</label>
                  <div class="form-control">
                    <input
                      v-model="settings.basic.email"
                      type="email"
                      class="form-input"
                      placeholder="请输入邮箱地址"
                    />
                    <div class="form-hint">用于找回密码和接收通知</div>
                  </div>
                </div>

                <div class="form-row form-row-last">
                  <label class="form-label">个人简介</label>
                  <div class="form-control">
                    <textarea
                      v-model="settings.basic.bio"
                      class="form-textarea"
                      rows="3"
                      placeholder="一句话介绍你自己..."
                    ></textarea>
                  </div>
                </div>
              </div>
            </div>

            <div v-else-if="activeNav === 'gen-params'" class="content-section">
              <div class="section-card">
                <div class="section-title">生成参数</div>

                <div class="form-row">
                  <label class="form-label">大纲目标字数</label>
                  <div class="form-control">
                    <input
                      v-model.number="settings.generation.outlineTargetWords"
                      type="number"
                      class="form-input form-input-sm"
                      min="100"
                      step="100"
                    />
                    <div class="form-hint">单章大纲生成目标字数</div>
                  </div>
                </div>

                <div class="form-row">
                  <label class="form-label">正文目标字数</label>
                  <div class="form-control">
                    <input
                      v-model.number="settings.generation.contentTargetWords"
                      type="number"
                      class="form-input form-input-sm"
                      min="500"
                      step="100"
                    />
                    <div class="form-hint">单章正文生成目标字数</div>
                  </div>
                </div>

                <div class="form-row form-row-last">
                  <label class="form-label">流式生成</label>
                  <div class="form-control">
                    <label class="switch-label">
                      <input
                        v-model="settings.generation.streaming"
                        type="checkbox"
                        class="switch-input"
                      />
                      <span class="switch-track"></span>
                      <span class="switch-thumb"></span>
                      <span class="switch-text">启用流式输出</span>
                    </label>
                  </div>
                </div>
              </div>
            </div>

            <div v-else-if="activeNav === 'ai-model'" class="content-section">
              <div class="section-card">
                <div class="section-title">AI模型设置</div>

                <div class="form-row">
                  <label class="form-label">LLM 提供商</label>
                  <div class="form-control">
                    <select v-model="settings.ai.provider" class="form-select">
                      <option value="openai">OpenAI 兼容</option>
                      <option value="anthropic">Anthropic</option>
                      <option value="ollama">Ollama 本地</option>
                    </select>
                  </div>
                </div>

                <div class="form-row">
                  <label class="form-label">API Base URL</label>
                  <div class="form-control">
                    <input
                      v-model="settings.ai.baseUrl"
                      type="text"
                      class="form-input"
                      :placeholder="PROVIDER_DEFAULTS[settings.ai.provider]?.placeholder || '由用户填写'"
                    />
                  </div>
                </div>

                <div class="form-row">
                  <label class="form-label">API Key</label>
                  <div class="form-control">
                    <div class="password-field">
                      <input
                        v-model="settings.ai.apiKey"
                        :type="showApiKey ? 'text' : 'password'"
                        class="form-input"
                        placeholder="sk-..."
                      />
                      <button class="password-toggle" @click="showApiKey = !showApiKey">
                        <Eye v-if="!showApiKey" class="toggle-icon" />
                        <EyeOff v-else class="toggle-icon" />
                      </button>
                    </div>
                    <div class="form-hint">密钥仅在本地存储，不会上传至服务器</div>
                    <div v-if="settings.ai.provider === 'ollama'" class="form-hint" style="color: var(--xy-text-secondary)">
                      Ollama 本地部署无需填写 API Key，请确保 Ollama 服务已启动
                    </div>
                  </div>
                </div>

                <div class="form-row">
                  <label class="form-label">默认模型</label>
                  <div class="form-control">
                    <input
                      v-model="settings.ai.model"
                      type="text"
                      class="form-input"
                      placeholder="由用户填写"
                    />
                  </div>
                </div>

                <div class="form-row form-row-last">
                  <label class="form-label"></label>
                  <div class="form-control">
                    <button
                      class="btn btn-ghost"
                      :disabled="testConnLoading"
                      @click="handleTestConnection"
                    >
                      <Bolt class="btn-icon" />
                      <span>{{ testConnLoading ? '测试中...' : '测试连接' }}</span>
                    </button>
                    <span v-if="testConnStatus === 'ok'" class="status-badge status-success"
                      >连接成功</span
                    >
                    <span v-else-if="testConnStatus === 'fail'" class="status-badge status-error"
                      >连接失败</span
                    >
                    <span v-else class="status-badge status-info">未测试</span>
                  </div>
                </div>
              </div>

              <div class="section-card">
                <div class="section-title">创作参数</div>

                <div class="form-row">
                  <label class="form-label">Temperature</label>
                  <div class="form-control">
                    <div class="slider-row">
                      <input
                        v-model.number="settings.ai.temperature"
                        type="range"
                        class="slider-track"
                        min="0"
                        max="2"
                        step="0.1"
                      />
                      <span class="slider-value">{{ settings.ai.temperature.toFixed(1) }}</span>
                    </div>
                  </div>
                </div>

                <div class="form-row">
                  <label class="form-label">Max Tokens</label>
                  <div class="form-control">
                    <input
                      v-model.number="settings.ai.maxTokens"
                      type="number"
                      class="form-input form-input-sm"
                      min="512"
                      max="16384"
                      step="256"
                    />
                    <div class="form-hint">范围 512 - 16384</div>
                  </div>
                </div>

                <div class="form-row">
                  <label class="form-label">Top P</label>
                  <div class="form-control">
                    <div class="slider-row">
                      <input
                        v-model.number="settings.ai.topP"
                        type="range"
                        class="slider-track"
                        min="0"
                        max="1"
                        step="0.05"
                      />
                      <span class="slider-value">{{ settings.ai.topP.toFixed(2) }}</span>
                    </div>
                  </div>
                </div>

                <div class="form-row form-row-last">
                  <label class="form-label">生成风格</label>
                  <div class="form-control">
                    <select v-model="settings.ai.style" class="form-select">
                      <option value="balanced">均衡</option>
                      <option value="creative">创意</option>
                      <option value="precise">严谨</option>
                      <option value="concise">简洁</option>
                      <option value="ornate">华丽</option>
                    </select>
                  </div>
                </div>
              </div>

              <div class="section-card">
                <div class="section-title">质量门禁</div>

                <div class="form-row">
                  <label class="form-label">开启质量检查</label>
                  <div class="form-control">
                    <label class="switch-label">
                      <input
                        v-model="settings.review.enable"
                        type="checkbox"
                        class="switch-input"
                      />
                      <span class="switch-track"></span>
                      <span class="switch-thumb"></span>
                      <span class="switch-text">启用章节生成后的质量检查</span>
                    </label>
                  </div>
                </div>

                <div class="form-row">
                  <label class="form-label">检查项</label>
                  <div class="form-control">
                    <div class="checkbox-group">
                      <label v-for="item in checkItems" :key="item.value" class="checkbox-item">
                        <input
                          v-model="settings.review.checkItems"
                          type="checkbox"
                          :value="item.value"
                          class="checkbox-input"
                        />
                        <span class="checkbox-box">
                          <Check
                            v-if="settings.review.checkItems.includes(item.value)"
                            class="checkbox-check"
                          />
                        </span>
                        <span class="checkbox-text">{{ item.label }}</span>
                      </label>
                    </div>
                  </div>
                </div>

                <div class="form-row form-row-last">
                  <label class="form-label">最低通过分</label>
                  <div class="form-control">
                    <div class="slider-row">
                      <input
                        v-model.number="settings.review.minScore"
                        type="range"
                        class="slider-track"
                        min="0"
                        max="100"
                        step="1"
                      />
                      <span class="slider-value">{{ settings.review.minScore }}</span>
                    </div>
                    <div class="form-hint">章节综合评分低于此分数将标记为待修订</div>
                  </div>
                </div>
              </div>
            </div>

            <div v-else-if="activeNav === 'theme'" class="content-section">
              <div class="section-card">
                <div class="section-title">界面主题</div>

                <div class="form-row">
                  <label class="form-label">显示模式</label>
                  <div class="form-control">
                    <div class="theme-options">
                      <div
                        :class="['theme-option', { active: settings.theme.mode === 'light' }]"
                        @click="settings.theme.mode = 'light'"
                      >
                        <div class="theme-preview theme-light"></div>
                        <span class="theme-label">浅色</span>
                      </div>
                      <div
                        :class="['theme-option', { active: settings.theme.mode === 'dark' }]"
                        @click="settings.theme.mode = 'dark'"
                      >
                        <div class="theme-preview theme-dark"></div>
                        <span class="theme-label">深色</span>
                      </div>
                      <div
                        :class="['theme-option', { active: settings.theme.mode === 'abyss' }]"
                        @click="settings.theme.mode = 'abyss'"
                      >
                        <div class="theme-preview theme-abyss"></div>
                        <span class="theme-label">星渊</span>
                      </div>
                      <div
                        :class="['theme-option', { active: settings.theme.mode === 'system' }]"
                        @click="settings.theme.mode = 'system'"
                      >
                        <div class="theme-preview theme-system"></div>
                        <span class="theme-label">跟随系统</span>
                      </div>
                    </div>
                  </div>
                </div>

                <div class="form-row">
                  <label class="form-label">主题色</label>
                  <div class="form-control">
                    <div class="color-options">
                      <div
                        v-for="color in accentColors"
                        :key="color.value"
                        :class="[
                          'color-option',
                          { active: settings.theme.accentColor === color.value },
                        ]"
                        :style="{ '--color': color.hex }"
                        @click="settings.theme.accentColor = color.value"
                      ></div>
                    </div>
                  </div>
                </div>

                <div class="form-row form-row-last">
                  <label class="form-label">字体大小</label>
                  <div class="form-control">
                    <select v-model="settings.theme.fontSize" class="form-select">
                      <option value="small">小</option>
                      <option value="medium">中</option>
                      <option value="large">大</option>
                    </select>
                  </div>
                </div>
              </div>
            </div>

            <div v-else-if="activeNav === 'quality'" class="content-section">
              <div class="section-card">
                <div class="section-title">质量阈值</div>

                <div class="form-row">
                  <label class="form-label">人物一致性</label>
                  <div class="form-control">
                    <div class="slider-row">
                      <input
                        v-model.number="settings.quality.characterThreshold"
                        type="range"
                        class="slider-track"
                        min="0"
                        max="1"
                        step="0.05"
                      />
                      <span class="slider-value">{{
                        settings.quality.characterThreshold.toFixed(2)
                      }}</span>
                    </div>
                    <div class="form-hint">低于此阈值将标记人物偏差</div>
                  </div>
                </div>

                <div class="form-row form-row-last">
                  <label class="form-label">剧情密度</label>
                  <div class="form-control">
                    <div class="slider-row">
                      <input
                        v-model.number="settings.quality.plotDensityThreshold"
                        type="range"
                        class="slider-track"
                        min="0"
                        max="1"
                        step="0.05"
                      />
                      <span class="slider-value">{{
                        settings.quality.plotDensityThreshold.toFixed(2)
                      }}</span>
                    </div>
                    <div class="form-hint">低于此阈值将标记剧情稀薄</div>
                  </div>
                </div>
              </div>
            </div>

            <div v-else-if="activeNav === 'style'" class="content-section">
              <div class="section-card">
                <div class="section-title">文风设置</div>

                <div class="form-row">
                  <label class="form-label">样本数量</label>
                  <div class="form-control">
                    <input
                      v-model.number="settings.style.voiceSampleSize"
                      type="number"
                      class="form-input form-input-sm"
                      min="1"
                      step="1"
                    />
                    <div class="form-hint">用于校准文风的样本段落数</div>
                  </div>
                </div>

                <div class="form-row form-row-last">
                  <label class="form-label">漂移阈值</label>
                  <div class="form-control">
                    <div class="slider-row">
                      <input
                        v-model.number="settings.style.driftThreshold"
                        type="range"
                        class="slider-track"
                        min="0"
                        max="1"
                        step="0.05"
                      />
                      <span class="slider-value">{{
                        settings.style.driftThreshold.toFixed(2)
                      }}</span>
                    </div>
                    <div class="form-hint">文风偏移超过此阈值将告警</div>
                  </div>
                </div>
              </div>
            </div>

            <div v-else-if="activeNav === 'export'" class="content-section">
              <div class="section-card">
                <div class="section-title">导出设置</div>

                <div class="form-row">
                  <label class="form-label">默认格式</label>
                  <div class="form-control">
                    <select v-model="settings.export.defaultFormat" class="form-select">
                      <option value="markdown">Markdown</option>
                      <option value="txt">纯文本</option>
                      <option value="docx">Word</option>
                      <option value="epub">EPUB</option>
                    </select>
                  </div>
                </div>

                <div class="form-row form-row-last">
                  <label class="form-label">包含元数据</label>
                  <div class="form-control">
                    <label class="switch-label">
                      <input
                        v-model="settings.export.includeMetadata"
                        type="checkbox"
                        class="switch-input"
                      />
                      <span class="switch-track"></span>
                      <span class="switch-thumb"></span>
                      <span class="switch-text">导出时附带章节元信息</span>
                    </label>
                  </div>
                </div>
              </div>

              <div class="section-card">
                <div class="section-title">立即导出</div>

                <div class="form-row">
                  <label class="form-label">导出当前小说</label>
                  <div class="form-control">
                    <div class="export-actions">
                      <button
                        v-for="fmt in exportFormats"
                        :key="fmt.format"
                        class="btn btn-export"
                        :disabled="exportLoading"
                        @click="handleExport(fmt.format)"
                      >
                        <Download class="btn-icon" />
                        <span>{{ fmt.label }}</span>
                      </button>
                    </div>
                    <div v-if="exportLoading" class="form-hint">正在导出，请稍候…</div>
                    <div v-else-if="exportMessage" class="form-hint export-success">
                      {{ exportMessage }}
                    </div>
                    <div v-else-if="exportError" class="form-hint export-error">
                      {{ exportError }}
                    </div>
                    <div v-else class="form-hint">选择格式后立即下载当前小说全文</div>
                  </div>
                </div>
              </div>
            </div>

            <div v-else class="content-placeholder">
              <component :is="currentNavIcon" class="placeholder-icon" />
              <p class="placeholder-text">{{ currentPageTitle }}</p>
              <p class="placeholder-desc">请选择左侧设置项</p>
            </div>
          </div>
        </div>

        <footer class="main-footer">
          <button class="btn btn-ghost" @click="resetSettings">
            <Refresh class="btn-icon" />
            <span>重置为默认</span>
          </button>
          <div class="footer-actions">
            <button class="btn btn-primary" @click="saveSettings()">
              <DeviceFloppy class="btn-icon" />
              <span>保存设置</span>
            </button>
          </div>
        </footer>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useSettingsStore } from '@/stores/settings'
import { downloadExport } from '@/api/export'
import { testConnection } from '@/api/settings'
import { useCurrentNovelId } from '@/composables/useCurrentNovelId'
import { toast } from '@/utils/toast'
import { useThemeStore } from '@/stores/theme'
import {
  Settings,
  ChevronRight,
  Eye,
  EyeOff,
  Check,
  DeviceFloppy,
  Refresh,
  Bolt,
  Book,
  Target,
  Robot,
  Cpu,
  Palette,
  Keyboard,
  InfoCircle,
  ArrowLeft,
  Download,
} from '@vicons/tabler'

const router = useRouter()
const settingsStore = useSettingsStore()
const { novelId } = useCurrentNovelId()

const activeNav = ref('ai-model')

const showApiKey = ref(false)

const novelSettingsItems = [
  { key: 'basic', label: '基础信息', icon: Book },
  { key: 'gen-params', label: '生成参数', icon: Target },
  { key: 'ai-model', label: 'AI参数', icon: Robot },
]

const globalSettingsItems = [
  { key: 'quality', label: '质量阈值', icon: Cpu },
  { key: 'theme', label: '界面主题', icon: Palette },
  { key: 'style', label: '文风设置', icon: Keyboard },
  { key: 'export', label: '导出设置', icon: InfoCircle },
]

const checkItems = [
  { label: '逻辑连贯性', value: 'logic' },
  { label: '人物一致性', value: 'character' },
  { label: '设定一致性', value: 'setting' },
  { label: '文笔流畅度', value: 'writing' },
]

const accentColors = [
  { value: 'indigo', hex: '#6366f1' },
  { value: 'violet', hex: '#8b5cf6' },
  { value: 'rose', hex: '#f43f5e' },
  { value: 'amber', hex: '#f59e0b' },
  { value: 'emerald', hex: '#10b981' },
  { value: 'cyan', hex: '#06b6d4' },
]

interface NestedSettings {
  basic: { username: string; penName: string; email: string; bio: string }
  ai: {
    provider: string
    baseUrl: string
    apiKey: string
    model: string
    temperature: number
    maxTokens: number
    topP: number
    style: string
  }
  review: { enable: boolean; checkItems: string[]; minScore: number }
  theme: { mode: string; accentColor: string; fontSize: string }
  generation: { outlineTargetWords: number; contentTargetWords: number; streaming: boolean }
  quality: { characterThreshold: number; plotDensityThreshold: number }
  style: { voiceSampleSize: number; driftThreshold: number }
  export: { defaultFormat: string; includeMetadata: boolean }
}

const defaultSettings: NestedSettings = {
  basic: {
    username: '创作者',
    penName: '',
    email: '',
    bio: '',
  },
  ai: {
    provider: 'ollama',
    baseUrl: 'http://localhost:11434/v1',
    apiKey: '',
    model: 'qwen2.5:7b',
    temperature: 0.7,
    maxTokens: 4096,
    topP: 0.9,
    style: 'balanced',
  },
  review: {
    enable: true,
    checkItems: ['logic', 'character'],
    minScore: 60,
  },
  theme: {
    mode: 'abyss',
    accentColor: 'indigo',
    fontSize: 'medium',
  },
  generation: {
    outlineTargetWords: 300,
    contentTargetWords: 3000,
    streaming: true,
  },
  quality: {
    characterThreshold: 0.8,
    plotDensityThreshold: 0.6,
  },
  style: {
    voiceSampleSize: 5,
    driftThreshold: 0.3,
  },
  export: {
    defaultFormat: 'md',
    includeMetadata: true,
  },
}

function deepMerge<T extends Record<string, unknown>>(target: T, source: Partial<T>): T {
  const result = JSON.parse(JSON.stringify(target)) as T
  for (const key in source) {
    if (Object.prototype.hasOwnProperty.call(source, key)) {
      const srcVal = source[key]
      const tgtVal = result[key]
      if (
        srcVal !== undefined &&
        srcVal !== null &&
        typeof srcVal === 'object' &&
        !Array.isArray(srcVal) &&
        typeof tgtVal === 'object' &&
        !Array.isArray(tgtVal)
      ) {
        result[key] = deepMerge(
          (tgtVal as Record<string, unknown>) || {},
          srcVal as Record<string, unknown>
        ) as T[Extract<keyof T, string>]
      } else if (srcVal !== undefined) {
        result[key] = srcVal as T[Extract<keyof T, string>]
      }
    }
  }
  return result
}

function setGroup<K extends keyof NestedSettings>(
  nested: Partial<NestedSettings>,
  key: K,
  values: Partial<NestedSettings[K]>
) {
  nested[key] = { ...(nested[key] || {}), ...values } as NestedSettings[K]
}

function flatToNested(flat: Record<string, string>): Partial<NestedSettings> {
  const n: Partial<NestedSettings> = {}

  if ('username' in flat) setGroup(n, 'basic', { username: flat.username })
  if ('pen_name' in flat) setGroup(n, 'basic', { penName: flat.pen_name })
  if ('email' in flat) setGroup(n, 'basic', { email: flat.email })
  if ('bio' in flat) setGroup(n, 'basic', { bio: flat.bio })

  if ('ai_provider' in flat) setGroup(n, 'ai', { provider: flat.ai_provider })
  if ('default_model' in flat) setGroup(n, 'ai', { model: flat.default_model })
  if ('api_base_url' in flat) setGroup(n, 'ai', { baseUrl: flat.api_base_url })
  if ('api_key' in flat) setGroup(n, 'ai', { apiKey: flat.api_key })
  if ('temperature' in flat) setGroup(n, 'ai', { temperature: Number(flat.temperature) })
  if ('max_tokens' in flat) setGroup(n, 'ai', { maxTokens: Number(flat.max_tokens) })
  if ('top_p' in flat) setGroup(n, 'ai', { topP: Number(flat.top_p) })
  if ('generation_style' in flat) setGroup(n, 'ai', { style: flat.generation_style })

  if ('auto_review' in flat)
    setGroup(n, 'review', { enable: flat.auto_review === 'true' })
  if ('review_threshold' in flat)
    setGroup(n, 'review', { minScore: Number(flat.review_threshold) })
  if ('review_check_items' in flat)
    setGroup(n, 'review', {
      checkItems: flat.review_check_items ? flat.review_check_items.split(',') : [],
    })

  if ('theme' in flat) setGroup(n, 'theme', { mode: flat.theme })
  if ('accent_color' in flat) setGroup(n, 'theme', { accentColor: flat.accent_color })
  if ('font_size' in flat) setGroup(n, 'theme', { fontSize: flat.font_size })

  if ('outline_target_words' in flat)
    setGroup(n, 'generation', { outlineTargetWords: Number(flat.outline_target_words) })
  if ('content_target_words' in flat)
    setGroup(n, 'generation', { contentTargetWords: Number(flat.content_target_words) })
  if ('streaming' in flat)
    setGroup(n, 'generation', { streaming: flat.streaming === 'true' })

  if ('character_threshold' in flat)
    setGroup(n, 'quality', { characterThreshold: Number(flat.character_threshold) })
  if ('plot_density_threshold' in flat)
    setGroup(n, 'quality', { plotDensityThreshold: Number(flat.plot_density_threshold) })

  if ('voice_sample_size' in flat)
    setGroup(n, 'style', { voiceSampleSize: Number(flat.voice_sample_size) })
  if ('drift_threshold' in flat)
    setGroup(n, 'style', { driftThreshold: Number(flat.drift_threshold) })

  if ('default_export_format' in flat)
    setGroup(n, 'export', { defaultFormat: flat.default_export_format })
  if ('include_metadata' in flat)
    setGroup(n, 'export', { includeMetadata: flat.include_metadata === 'true' })

  return n
}

function nestedToFlat(nested: NestedSettings): Record<string, string> {
  const flat: Record<string, string> = {}

  if (nested.basic) {
    flat.username = nested.basic.username
    flat.pen_name = nested.basic.penName
    flat.email = nested.basic.email
    flat.bio = nested.basic.bio
  }
  if (nested.ai) {
    flat.ai_provider = nested.ai.provider
    flat.default_model = nested.ai.model
    flat.api_base_url = nested.ai.baseUrl
    flat.api_key = nested.ai.apiKey
    flat.temperature = String(nested.ai.temperature)
    flat.max_tokens = String(nested.ai.maxTokens)
    flat.top_p = String(nested.ai.topP)
    flat.generation_style = nested.ai.style
  }
  if (nested.review) {
    flat.auto_review = String(nested.review.enable)
    flat.review_threshold = String(nested.review.minScore)
    flat.review_check_items = (nested.review.checkItems || []).join(',')
  }
  if (nested.theme) {
    flat.theme = nested.theme.mode
    flat.accent_color = nested.theme.accentColor
    flat.font_size = nested.theme.fontSize
  }
  if (nested.generation) {
    flat.outline_target_words = String(nested.generation.outlineTargetWords)
    flat.content_target_words = String(nested.generation.contentTargetWords)
    flat.streaming = String(nested.generation.streaming)
  }
  if (nested.quality) {
    flat.character_threshold = String(nested.quality.characterThreshold)
    flat.plot_density_threshold = String(nested.quality.plotDensityThreshold)
  }
  if (nested.style) {
    flat.voice_sample_size = String(nested.style.voiceSampleSize)
    flat.drift_threshold = String(nested.style.driftThreshold)
  }
  if (nested.export) {
    flat.default_export_format = nested.export.defaultFormat
    flat.include_metadata = String(nested.export.includeMetadata)
  }

  return flat
}

const settings = ref(JSON.parse(JSON.stringify(defaultSettings)))

// 协议默认配置
const PROVIDER_DEFAULTS: Record<string, { baseUrl: string; model: string; placeholder: string }> = {
  openai: {
    baseUrl: 'https://api.openai.com/v1',
    model: 'gpt-4o',
    placeholder: '如 https://api.openai.com/v1',
  },
  anthropic: {
    baseUrl: 'https://api.anthropic.com',
    model: 'claude-sonnet-4-20250514',
    placeholder: '如 https://api.anthropic.com',
  },
  ollama: {
    baseUrl: 'http://localhost:11434/v1',
    model: 'qwen2.5:7b',
    placeholder: '默认 http://localhost:11434/v1',
  },
}

// 主题模式：通过 themeStore 统一管理（data-theme + naive-ui appTheme）
const themeStore = useThemeStore()
watch(
  () => settings.value.theme.mode,
  (mode) => {
    themeStore.setMode(mode as 'light' | 'dark' | 'abyss' | 'system')
  },
  { immediate: true }
)

// B7 修复：反向同步——主题经顶栏/快捷键切换后，Settings 选项高亮随之更新
watch(
  () => themeStore.mode,
  (mode) => {
    if (settings.value.theme.mode !== mode) {
      settings.value.theme.mode = mode
    }
  }
)

// 字体大小：通过根元素 font-size 缩放全部 rem 单位（CSS 变量 --xy-fs-* 均为 rem）
watch(
  () => settings.value.theme.fontSize,
  (size) => {
    const sizeMap: Record<string, string> = { small: '14px', medium: '16px', large: '18px' }
    document.documentElement.style.fontSize = sizeMap[size] || '16px'
  },
  { immediate: true }
)

// AI 协议切换：自动更新默认 URL 和模型
watch(
  () => settings.value.ai.provider,
  (newProvider) => {
    const defaults = PROVIDER_DEFAULTS[newProvider]
    if (defaults) {
      settings.value.ai.baseUrl = defaults.baseUrl
      settings.value.ai.model = defaults.model
    }
  }
)

const currentPageTitle = computed(() => {
  const allItems = [...novelSettingsItems, ...globalSettingsItems]
  const item = allItems.find((i) => i.key === activeNav.value)
  return item?.label || '设置'
})

const currentNavIcon = computed(() => {
  const allItems = [...novelSettingsItems, ...globalSettingsItems]
  const item = allItems.find((i) => i.key === activeNav.value)
  return item?.icon || Settings
})

async function saveSettings(silent = false) {
  // 将嵌套 UI 状态映射为后端扁平 Record<string, string>
  const backendData = nestedToFlat(settings.value)

  // 调用 store 保存到后端（store 内部会同时缓存到 localStorage）
  await settingsStore.saveSettings(backendData)

  // 仍然保持 localStorage 保存（作为本地缓存）
  localStorage.setItem('xy-settings', JSON.stringify(settings.value))
  if (!silent) {
    toast.success('设置已保存')
  }
}

async function resetSettings() {
  // 同时重置后端设置（审查报告 2.13）
  await settingsStore.resetSettings()
  settings.value = JSON.parse(JSON.stringify(defaultSettings))
  toast.success('已重置为默认设置')
}

// ===== 测试连接（审查报告 5.2）=====
const testConnLoading = ref(false)
const testConnStatus = ref<'idle' | 'ok' | 'fail'>('idle')

async function handleTestConnection() {
  testConnLoading.value = true
  testConnStatus.value = 'idle'
  try {
    // 先静默保存设置，使后端 LLM 配置即时生效（避免用旧配置测试）
    await saveSettings(true)
    const result = await testConnection({ _silent: true })
    if (result.ok) {
      testConnStatus.value = 'ok'
      toast.success('LLM 连接成功')
    } else {
      testConnStatus.value = 'fail'
      toast.error('连接失败，请检查配置')
    }
  } catch (e: unknown) {
    testConnStatus.value = 'fail'
    toast.error((e as Error)?.message || '连接失败，请检查配置')
  } finally {
    testConnLoading.value = false
  }
}

// ===== 导出功能 =====
const exportLoading = ref(false)
const exportMessage = ref('')
const exportError = ref('')

const exportFormats = [
  { format: 'txt', label: 'TXT 纯文本' },
  { format: 'md', label: 'Markdown' },
  { format: 'html', label: 'HTML' },
  { format: 'epub', label: 'EPUB 电子书' },
  { format: 'docx', label: 'DOCX 文档' },
]

async function handleExport(format: string) {
  if (!novelId.value) {
    exportError.value = '未找到当前小说'
    return
  }
  exportLoading.value = true
  exportError.value = ''
  exportMessage.value = ''
  try {
    const filename = `novel-${novelId.value}.${format}`
    await downloadExport(
      novelId.value,
      {
        format,
        scope: 'full',
        include_title_page: settings.value.export.includeMetadata,
        include_chapter_numbers: settings.value.export.includeMetadata,
        include_toc: settings.value.export.includeMetadata,
      },
      filename
    )
    exportMessage.value = `已导出 ${format.toUpperCase()} 格式`
  } catch (e: unknown) {
    exportError.value = (e as Error)?.message || '导出失败'
  } finally {
    exportLoading.value = false
  }
}

const saved = localStorage.getItem('xy-settings')
if (saved) {
  try {
    const data = JSON.parse(saved)
    if (data.basic) settings.value.basic = { ...settings.value.basic, ...data.basic }
    if (data.ai) settings.value.ai = { ...settings.value.ai, ...data.ai }
    if (data.review) settings.value.review = { ...settings.value.review, ...data.review }
    if (data.theme) settings.value.theme = { ...settings.value.theme, ...data.theme }
    if (data.generation)
      settings.value.generation = { ...settings.value.generation, ...data.generation }
    if (data.quality) settings.value.quality = { ...settings.value.quality, ...data.quality }
    if (data.style) settings.value.style = { ...settings.value.style, ...data.style }
    if (data.export) settings.value.export = { ...settings.value.export, ...data.export }
  } catch (e) {
    console.error('Failed to load settings:', e)
  }
}

onMounted(async () => {
  await settingsStore.fetchSettings()
  // 后端返回扁平数据，映射后合并到嵌套 UI 状态；若后端为空则 deepMerge 保持现有 localStorage 默认值
  const backendNested = flatToNested(settingsStore.settings)
  settings.value = deepMerge(settings.value, backendNested)
})
</script>

<style scoped>
.settings-page {
  min-height: 100vh;
  background: var(--xy-bg-page);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
}

.settings-container {
  width: 100%;
  max-width: 1000px;
  height: calc(100vh - 80px);
  display: flex;
  background: var(--xy-bg-canvas);
  border-radius: var(--xy-radius-2xl);
  border: 1px solid var(--xy-border-1);
  box-shadow: var(--xy-shadow-lg);
  overflow: hidden;
}

.settings-sidebar {
  width: 240px;
  flex-shrink: 0;
  background: var(--xy-surface-1);
  border-right: 1px solid var(--xy-border-1);
  display: flex;
  flex-direction: column;
}

.back-home-btn {
  display: flex;
  align-items: center;
  gap: var(--xy-space-2);
  height: 44px;
  padding: 0 var(--xy-space-5);
  background: transparent;
  border: none;
  border-bottom: 1px solid var(--xy-border-1);
  color: var(--xy-text-2);
  font-size: var(--xy-fs-sm);
  font-family: var(--xy-font-sans);
  font-weight: 500;
  cursor: pointer;
  flex-shrink: 0;
  width: 100%;
  transition:
    background-color var(--xy-dur-sm) var(--xy-ease-standard),
    color var(--xy-dur-sm) var(--xy-ease-standard);
}

.back-home-btn:hover {
  background: var(--xy-surface-hover);
  color: var(--xy-brand-starlight);
}

.back-icon {
  width: 16px;
  height: 16px;
}

.sidebar-header {
  height: 56px;
  display: flex;
  align-items: center;
  gap: var(--xy-space-3);
  padding: 0 var(--xy-space-5);
  border-bottom: 1px solid var(--xy-border-1);
  flex-shrink: 0;
}

.sidebar-icon {
  width: 20px;
  height: 20px;
  color: var(--xy-brand-starlight);
  filter: drop-shadow(0 0 6px rgba(196, 181, 253, 0.4));
}

.sidebar-title {
  font-family: var(--xy-font-display);
  font-size: var(--xy-fs-lg);
  font-weight: 600;
  color: var(--xy-text-1);
  letter-spacing: 0.01em;
}

.sidebar-nav {
  flex: 1;
  overflow-y: auto;
  padding: var(--xy-space-3) 0;
}

.nav-group {
  margin-bottom: var(--xy-space-5);
}

.nav-group-title {
  font-size: 11px;
  font-weight: 600;
  color: var(--xy-text-4);
  padding: 0 var(--xy-space-5);
  margin-bottom: var(--xy-space-1);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: var(--xy-space-2);
  height: 38px;
  padding: 0 var(--xy-space-5);
  cursor: pointer;
  font-size: var(--xy-fs-sm);
  color: var(--xy-text-2);
  transition: all var(--xy-dur-sm) var(--xy-ease-standard);
  position: relative;
  user-select: none;
  font-weight: 500;
}

.nav-item:hover {
  background: var(--xy-surface-hover);
  color: var(--xy-text-1);
}

.nav-item.active {
  background: var(--xy-brand-50);
  color: var(--xy-brand-700);
  font-weight: 600;
}

.nav-item.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 8px;
  bottom: 8px;
  width: 3px;
  border-radius: 0 3px 3px 0;
  background: var(--xy-brand-500);
  box-shadow: 0 0 8px rgba(124, 108, 191, 0.4);
}

.nav-item-icon {
  width: 16px;
  height: 16px;
  flex-shrink: 0;
}

.nav-item-text {
  flex: 1;
  min-width: 0;
}

.nav-item-arrow {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
  opacity: 0;
  color: var(--xy-text-4);
  transition: all var(--xy-dur-sm) var(--xy-ease-standard);
}

.nav-item:hover .nav-item-arrow,
.nav-item.active .nav-item-arrow {
  opacity: 1;
}

.settings-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.main-scroll {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}

.main-header {
  padding: var(--xy-space-6) var(--xy-space-8) 0;
}

.page-title {
  font-family: var(--xy-font-display);
  font-size: var(--xy-fs-2xl);
  font-weight: 600;
  color: var(--xy-text-1);
  letter-spacing: -0.01em;
}

.main-content {
  padding: var(--xy-space-6) var(--xy-space-8);
}

.content-section {
  display: flex;
  flex-direction: column;
  gap: var(--xy-space-5);
}

.section-card {
  background: var(--xy-surface-1);
  border-radius: var(--xy-radius-xl);
  padding: var(--xy-space-5) var(--xy-space-6);
  border: 1px solid var(--xy-border-1);
  transition: border-color var(--xy-dur-sm) var(--xy-ease-standard);
}

.section-card:hover {
  border-color: var(--xy-border-2);
}

.section-title {
  font-family: var(--xy-font-display);
  font-size: var(--xy-fs-md);
  font-weight: 600;
  color: var(--xy-text-1);
  padding-bottom: var(--xy-space-3);
  margin-bottom: var(--xy-space-5);
  border-bottom: 1px solid var(--xy-divider);
  letter-spacing: 0.01em;
}

.form-row {
  display: flex;
  align-items: flex-start;
  gap: var(--xy-space-4);
  margin-bottom: var(--xy-space-5);
}

.form-row-last {
  margin-bottom: 0;
}

.form-label {
  width: 120px;
  flex-shrink: 0;
  text-align: right;
  font-size: var(--xy-fs-sm);
  color: var(--xy-text-2);
  line-height: 40px;
  font-weight: 500;
}

.form-control {
  flex: 1;
  min-width: 0;
}

.form-input,
.form-select {
  height: 40px;
  width: 100%;
  padding: 0 var(--xy-space-3);
  border-radius: var(--xy-radius-md);
  border: 1px solid var(--xy-border-1);
  background: var(--xy-surface-2);
  color: var(--xy-text-1);
  font-size: var(--xy-fs-sm);
  font-family: var(--xy-font-sans);
  outline: none;
  font-weight: 500;
  transition: all var(--xy-dur-sm) var(--xy-ease-standard);
}

.form-textarea {
  width: 100%;
  padding: 10px var(--xy-space-3);
  border-radius: var(--xy-radius-md);
  border: 1px solid var(--xy-border-1);
  background: var(--xy-surface-2);
  color: var(--xy-text-1);
  font-size: var(--xy-fs-sm);
  font-family: var(--xy-font-sans);
  outline: none;
  line-height: var(--xy-lh-relaxed);
  resize: vertical;
  transition: all var(--xy-dur-sm) var(--xy-ease-standard);
}

.form-textarea::placeholder {
  color: var(--xy-text-4);
}

.form-textarea:focus {
  border-color: var(--xy-border-focus);
  box-shadow: var(--xy-shadow-focus-ring);
  background: var(--xy-surface-hover);
}

.form-input:hover,
.form-select:hover {
  border-color: var(--xy-border-2);
  background: var(--xy-surface-hover);
}

.form-input:focus,
.form-select:focus {
  border-color: var(--xy-border-focus);
  box-shadow: var(--xy-shadow-focus-ring);
  background: var(--xy-surface-hover);
}

.form-input::placeholder {
  color: var(--xy-text-4);
}

.form-input-sm {
  width: 140px;
  text-align: center;
  font-variant-numeric: tabular-nums;
}

.form-select {
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='none' stroke='%237d7598' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpath d='m6 9 6 6 6-6'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 12px center;
  padding-right: 32px;
  cursor: pointer;
}

.form-hint {
  font-size: var(--xy-fs-xs);
  color: var(--xy-text-4);
  margin-top: var(--xy-space-1);
}

.password-field {
  position: relative;
  display: flex;
  align-items: center;
}

.password-field .form-input {
  padding-right: var(--xy-space-8);
}

.password-toggle {
  position: absolute;
  right: var(--xy-space-2);
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: none;
  background: transparent;
  color: var(--xy-text-4);
  cursor: pointer;
  border-radius: var(--xy-radius-sm);
  transition: all var(--xy-dur-sm) var(--xy-ease-standard);
}

.password-toggle:hover {
  color: var(--xy-brand-starlight);
  background: var(--xy-surface-hover);
}

.toggle-icon {
  width: 16px;
  height: 16px;
}

.slider-row {
  display: flex;
  align-items: center;
  gap: var(--xy-space-3);
}

.slider-track {
  flex: 1;
  -webkit-appearance: none;
  appearance: none;
  height: 4px;
  border-radius: var(--xy-radius-full);
  background: var(--xy-surface-3);
  outline: none;
  cursor: pointer;
}

.slider-track::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--xy-brand-500), var(--xy-brand-700));
  border: 2px solid var(--xy-bg-canvas);
  cursor: pointer;
  transition: all var(--xy-dur-sm) var(--xy-ease-standard);
  box-shadow: 0 2px 6px rgba(124, 108, 191, 0.3);
}

.slider-track::-webkit-slider-thumb:hover {
  transform: scale(1.15);
  box-shadow:
    0 0 0 4px rgba(124, 108, 191, 0.15),
    0 2px 8px rgba(124, 108, 191, 0.3);
}

.slider-track::-moz-range-thumb {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--xy-brand-500), var(--xy-brand-700));
  border: 2px solid var(--xy-bg-canvas);
  cursor: pointer;
  box-shadow: 0 2px 6px rgba(124, 108, 191, 0.3);
}

.slider-value {
  min-width: 48px;
  text-align: right;
  font-size: var(--xy-fs-sm);
  font-variant-numeric: tabular-nums;
  color: var(--xy-brand-starlight);
  font-weight: 600;
}

.switch-label {
  display: flex;
  align-items: center;
  gap: var(--xy-space-3);
  cursor: pointer;
  user-select: none;
  position: relative;
}

.switch-input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}

.switch-track {
  position: relative;
  width: 40px;
  height: 22px;
  background: var(--xy-surface-3);
  border: 1px solid var(--xy-border-1);
  border-radius: 11px;
  transition: all var(--xy-dur-sm) var(--xy-ease-standard);
  flex-shrink: 0;
}

.switch-thumb {
  position: absolute;
  top: 3px;
  left: 3px;
  width: 16px;
  height: 16px;
  border-radius: 50%;
  background: var(--xy-text-3);
  transition: all var(--xy-dur-sm) var(--xy-ease-standard);
  pointer-events: none;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
}

.switch-input:checked + .switch-track {
  background: linear-gradient(135deg, var(--xy-brand-500), var(--xy-brand-600));
  border-color: transparent;
  box-shadow: 0 2px 8px rgba(124, 108, 191, 0.3);
}

.switch-input:checked + .switch-track + .switch-thumb {
  transform: translateX(18px);
  background: #fff;
}

.switch-text {
  font-size: var(--xy-fs-sm);
  color: var(--xy-text-2);
  font-weight: 500;
}

.checkbox-group {
  display: flex;
  flex-wrap: wrap;
  gap: var(--xy-space-3) var(--xy-space-6);
}

.checkbox-item {
  display: flex;
  align-items: center;
  gap: var(--xy-space-2);
  cursor: pointer;
  user-select: none;
}

.checkbox-input {
  position: absolute;
  opacity: 0;
  width: 0;
  height: 0;
}

.checkbox-box {
  width: 18px;
  height: 18px;
  border-radius: var(--xy-radius-sm);
  border: 1px solid var(--xy-border-2);
  background: var(--xy-surface-2);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--xy-dur-sm) var(--xy-ease-standard);
  flex-shrink: 0;
}

.checkbox-input:checked + .checkbox-box {
  background: linear-gradient(135deg, var(--xy-brand-500), var(--xy-brand-600));
  border-color: transparent;
  box-shadow: 0 2px 6px rgba(124, 108, 191, 0.3);
}

.checkbox-check {
  width: 12px;
  height: 12px;
  color: #fff;
}

.checkbox-text {
  font-size: var(--xy-fs-sm);
  color: var(--xy-text-2);
  font-weight: 500;
}

.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: var(--xy-fs-xs);
  font-weight: 600;
  margin-left: var(--xy-space-3);
  padding: 2px 8px;
  border-radius: var(--xy-radius-full);
}

.status-success {
  color: var(--xy-success);
  background: rgba(74, 222, 128, 0.1);
}

.status-error {
  color: var(--xy-error, #ef4444);
  background: rgba(248, 113, 113, 0.1);
}

.status-info {
  color: var(--xy-info);
  background: rgba(96, 165, 250, 0.1);
}

.status-icon {
  width: 14px;
  height: 14px;
}

.theme-options {
  display: flex;
  gap: var(--xy-space-4);
}

.theme-option {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--xy-space-2);
  cursor: pointer;
  padding: var(--xy-space-2);
  border-radius: var(--xy-radius-lg);
  border: 2px solid transparent;
  transition: all var(--xy-dur-sm) var(--xy-ease-standard);
}

.theme-option:hover {
  background: var(--xy-surface-hover);
}

.theme-option.active {
  border-color: var(--xy-brand-500);
  background: color-mix(in srgb, var(--xy-brand-500) 6%, transparent);
}

.theme-preview {
  width: 64px;
  height: 48px;
  border-radius: var(--xy-radius-md);
  border: 1px solid var(--xy-border-2);
  overflow: hidden;
}

.theme-light {
  background: linear-gradient(180deg, #ffffff 0%, #f3f4f6 100%);
}

.theme-dark {
  background: linear-gradient(180deg, var(--xy-bg-canvas) 0%, var(--xy-bg-page) 100%);
}

.theme-abyss {
  position: relative;
  background: linear-gradient(135deg, #0f0a1e 0%, #1a1033 50%, #2d1b4e 100%);
  border-color: var(--xy-brand-500);
}

.theme-abyss::after {
  content: '';
  position: absolute;
  top: 8px;
  right: 8px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--xy-brand-400);
  box-shadow: 0 0 8px var(--xy-brand-400);
}

.theme-system {
  background: linear-gradient(90deg, #ffffff 0%, #ffffff 50%, #1f2937 50%, #1f2937 100%);
}

.theme-label {
  font-size: var(--xy-fs-sm);
  color: var(--xy-text-2);
  font-weight: 500;
}

.color-options {
  display: flex;
  gap: var(--xy-space-3);
  flex-wrap: wrap;
}

.color-option {
  width: 30px;
  height: 30px;
  border-radius: 50%;
  background: var(--color);
  cursor: pointer;
  border: 3px solid transparent;
  transition: all var(--xy-dur-sm) var(--xy-ease-standard);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
}

.color-option:hover {
  transform: scale(1.1);
}

.color-option.active {
  border-color: var(--xy-text-1);
  transform: scale(1.1);
  box-shadow:
    0 0 0 3px var(--xy-bg-canvas),
    0 4px 12px rgba(0, 0, 0, 0.2);
}

.content-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--xy-space-16) 0;
  text-align: center;
}

.placeholder-icon {
  width: 48px;
  height: 48px;
  color: var(--xy-text-4);
  margin-bottom: var(--xy-space-4);
  opacity: 0.5;
}

.placeholder-text {
  font-family: var(--xy-font-display);
  font-size: var(--xy-fs-lg);
  font-weight: 600;
  color: var(--xy-text-2);
  margin-bottom: var(--xy-space-2);
}

.placeholder-desc {
  font-size: var(--xy-fs-sm);
  color: var(--xy-text-4);
}

.main-footer {
  height: 68px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--xy-space-8);
  border-top: 1px solid var(--xy-border-1);
  flex-shrink: 0;
  background: var(--xy-surface-1);
}

.footer-actions {
  display: flex;
  gap: var(--xy-space-3);
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--xy-space-2);
  font-family: var(--xy-font-sans);
  font-weight: 600;
  font-size: var(--xy-fs-sm);
  border-radius: var(--xy-radius-md);
  cursor: pointer;
  transition: all var(--xy-dur-sm) var(--xy-ease-standard);
  white-space: nowrap;
  user-select: none;
  letter-spacing: 0.01em;
}

.btn:active {
  transform: scale(0.98);
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  pointer-events: none;
}

.btn-icon {
  width: 16px;
  height: 16px;
}

.btn-primary {
  height: 40px;
  padding: 0 var(--xy-space-5);
  background: linear-gradient(135deg, var(--xy-brand-500), var(--xy-brand-600));
  color: #fff;
  border: none;
  box-shadow: 0 4px 12px rgba(124, 108, 191, 0.3);
}

.btn-primary:hover {
  transform: translateY(-1px);
  box-shadow: 0 6px 18px rgba(124, 108, 191, 0.4);
  filter: brightness(1.05);
}

.btn-ghost {
  height: 40px;
  padding: 0 var(--xy-space-4);
  background: transparent;
  color: var(--xy-text-2);
  border: 1px solid var(--xy-border-1);
  font-weight: 500;
}

.btn-ghost:hover {
  background: var(--xy-surface-hover);
  color: var(--xy-text-1);
  border-color: var(--xy-border-2);
}

.export-actions {
  display: flex;
  gap: var(--xy-space-3);
  flex-wrap: wrap;
}

.btn-export {
  height: 40px;
  padding: 0 var(--xy-space-4);
  background: var(--xy-surface-2);
  color: var(--xy-text-2);
  border: 1px solid var(--xy-border-1);
  font-weight: 500;
}

.btn-export:hover:not(:disabled) {
  background: color-mix(in srgb, var(--xy-brand-500) 8%, transparent);
  color: var(--xy-brand-starlight);
  border-color: var(--xy-brand-500);
}

.btn-export:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.export-success {
  color: var(--xy-success);
}

.export-error {
  color: var(--xy-error, #ef4444);
}
</style>
