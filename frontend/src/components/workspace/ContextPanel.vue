<template>
  <div class="context-panel">
    <!-- 标签栏 -->
    <div class="tab-bar">
      <div class="tab-scroll">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          class="tab-item"
          :class="{ 'tab-active': activeTab === tab.key }"
          @click="activeTab = tab.key"
        >
          {{ tab.label }}
        </button>
      </div>
    </div>

    <!-- 内容区 -->
    <div class="panel-content">
      <!-- 叙事简报 -->
      <div v-show="activeTab === 'briefing'" class="tab-content">
        <!-- 综合质量评分卡片 -->
        <div class="quality-card">
          <div class="card-title">综合质量评分</div>
          <div class="quality-ring-wrap">
            <svg class="quality-ring" viewBox="0 0 120 120">
              <circle
                cx="60"
                cy="60"
                r="52"
                fill="none"
                stroke="var(--xy-surface-2)"
                stroke-width="8"
              />
              <circle
                cx="60"
                cy="60"
                r="52"
                fill="none"
                stroke="var(--xy-brand-500)"
                stroke-width="8"
                :stroke-dasharray="qualityDash"
                stroke-dashoffset="0"
                stroke-linecap="round"
                transform="rotate(-90 60 60)"
                style="transition: stroke-dasharray 0.5s ease"
              />
            </svg>
            <div class="quality-score">
              <span class="score-num">{{ qualityLoading ? '--' : qualityScore || '--' }}</span>
              <span class="score-unit">分</span>
            </div>
          </div>
          <div class="quality-desc">
            <template v-if="qualityError">{{ qualityError }}</template>
            <template v-else-if="!qualityScore">开始创作后显示评分</template>
            <template v-else-if="reviewGrade">评级 {{ reviewGrade }}</template>
            <template v-else>当前章节张力分</template>
          </div>
        </div>

        <!-- 故事线进度 -->
        <div class="section">
          <div class="section-title">故事线进度</div>
          <div class="progress-list">
            <div class="progress-item">
              <div class="progress-header">
                <span class="progress-label">主线</span>
                <span class="progress-value">0%</span>
              </div>
              <div class="progress-bar">
                <div class="progress-fill progress-main" style="width: 0%"></div>
              </div>
            </div>
            <div class="progress-item">
              <div class="progress-header">
                <span class="progress-label">副线</span>
                <span class="progress-value">0%</span>
              </div>
              <div class="progress-bar">
                <div class="progress-fill progress-sub" style="width: 0%"></div>
              </div>
            </div>
            <div class="progress-item">
              <div class="progress-header">
                <span class="progress-label">感情线</span>
                <span class="progress-value">0%</span>
              </div>
              <div class="progress-bar">
                <div class="progress-fill progress-romance" style="width: 0%"></div>
              </div>
            </div>
          </div>
        </div>

        <!-- 当前视角 -->
        <div class="section">
          <div class="section-title">当前视角</div>
          <div v-if="briefingLoading" class="empty-text">加载中…</div>
          <div v-else-if="briefingError" class="empty-text">加载失败：{{ briefingError }}</div>
          <div
            v-else-if="ironLock && ironLock.character_whitelist.length"
            class="character-list-mini"
          >
            <div
              v-for="name in ironLock.character_whitelist"
              :key="name"
              class="character-mini-card"
            >
              <div class="char-mini-avatar">{{ name.slice(0, 1) }}</div>
              <div class="char-mini-info">
                <span class="char-mini-name">{{ name }}</span>
              </div>
            </div>
          </div>
          <p v-else class="empty-text">暂无人物</p>
        </div>

        <!-- AI建议 -->
        <div class="section">
          <div class="section-title">AI 建议</div>
          <div v-if="briefingLoading" class="empty-text">加载中…</div>
          <div v-else-if="briefingError" class="empty-text">加载失败：{{ briefingError }}</div>
          <div v-else-if="memoryFacts.length" class="knowledge-list">
            <div v-for="f in memoryFacts.slice(0, 5)" :key="f.id" class="knowledge-card">
              <span class="triple-subject">{{ f.subject }}</span>
              <span class="triple-predicate">{{ f.predicate }}</span>
              <span class="triple-object">{{ f.object_value }}</span>
            </div>
          </div>
          <p v-else class="empty-text">开始写作后显示AI建议</p>
        </div>
      </div>

      <!-- 当前语境 -->
      <div v-show="activeTab === 'context'" class="tab-content">
        <!-- 前文摘要 -->
        <div class="section">
          <button class="section-header" @click="summaryExpanded = !summaryExpanded">
            <span class="section-title-left">
              <FileText class="section-icon" />
              前文摘要
            </span>
            <ChevronDown v-if="summaryExpanded" class="chevron-icon" />
            <ChevronRight v-else class="chevron-icon" />
          </button>
          <div v-show="summaryExpanded" class="summary-list">
            <div v-if="contextLoading" class="empty-text">加载中…</div>
            <div v-else-if="contextError" class="empty-text">加载失败：{{ contextError }}</div>
            <p v-else-if="memoryBeats.length === 0" class="empty-text">暂无章节摘要</p>
            <div v-for="b in memoryBeats.slice(0, 10)" v-else :key="b.id" class="summary-card">
              <div class="summary-chapter">
                第 {{ b.chapter_index }} 章 · {{ beatTypeMap[b.beat_type] || b.beat_type }}
              </div>
              <p class="summary-text">{{ b.content }}</p>
            </div>
          </div>
        </div>

        <!-- 在场人物 -->
        <div class="section">
          <div class="section-header-static">
            <Users class="section-icon" />
            <span class="section-title-text">在场人物</span>
          </div>
          <div v-if="contextLoading" class="empty-text">加载中…</div>
          <div v-else-if="contextError" class="empty-text">加载失败：{{ contextError }}</div>
          <div v-else-if="sceneCharacters.length" class="character-list-mini">
            <div
              v-for="c in sceneCharacters.slice(0, 8)"
              :key="c.id"
              class="character-mini-card"
            >
              <div class="char-mini-avatar">{{ c.name.slice(0, 1) }}</div>
              <div class="char-mini-info">
                <span class="char-mini-name">{{ c.name }}</span>
                <span v-if="c.role" class="char-mini-role">{{ c.role }}</span>
              </div>
            </div>
          </div>
          <p v-else class="empty-text">暂无人物</p>
        </div>

        <!-- 地点与物品 -->
        <div class="section">
          <div class="section-header-static">
            <MapPin class="section-icon" />
            <span class="section-title-text">地点与物品</span>
          </div>
          <div v-if="contextLoading" class="empty-text">加载中…</div>
          <div v-else-if="contextError" class="empty-text">加载失败：{{ contextError }}</div>
          <div v-else-if="sceneSettings.length" class="setting-list-mini">
            <div
              v-for="s in sceneSettings.slice(0, 6)"
              :key="s.id"
              class="setting-mini-card"
            >
              <span class="setting-mini-name">{{ s.name }}</span>
              <span class="setting-mini-cat">{{ settingTypeMap[s.setting_type] || s.setting_type }}</span>
            </div>
          </div>
          <p v-else class="empty-text">暂无地点物品</p>
        </div>

        <!-- 伏笔提醒 -->
        <div class="section">
          <div class="section-header-static">
            <AlertTriangle class="section-icon section-icon-warning" />
            <span class="section-title-text">伏笔提醒</span>
          </div>
          <div v-if="pendingLoading" class="empty-text">加载中…</div>
          <div v-else-if="pendingError" class="empty-text">加载失败：{{ pendingError }}</div>
          <div v-else-if="pendingReport && pendingReport.total_pending > 0">
            <div class="foreshadow-stats">
              <div class="foreshadow-stat">
                <span class="foreshadow-stat-num">{{ pendingReport.total_pending }}</span>
                <span class="foreshadow-stat-label">待回收</span>
              </div>
              <div class="foreshadow-stat">
                <span class="foreshadow-stat-num">{{ pendingReport.high_priority }}</span>
                <span class="foreshadow-stat-label">高优先级</span>
              </div>
            </div>
            <div class="foreshadow-list-mini">
              <div
                v-for="f in pendingReport.foreshadows.slice(0, 3)"
                :key="f.id"
                class="foreshadow-mini-card"
              >
                <span class="foreshadow-mini-title">{{ f.title }}</span>
                <span class="foreshadow-mini-status" :class="`status-${f.priority}`">{{
                  f.priority === 'high' ? '紧急' : f.priority === 'medium' ? '中' : '低'
                }}</span>
              </div>
            </div>
          </div>
          <p v-else class="empty-text">暂无待回收伏笔</p>
        </div>
      </div>

      <!-- 伏笔账本 -->
      <div v-show="activeTab === 'foreshadow'" class="tab-content">
        <div class="section">
          <div class="section-header-static">
            <Bookmark class="section-icon" />
            <span class="section-title-text">伏笔账本</span>
          </div>
          <div class="foreshadow-stats">
            <div class="foreshadow-stat">
              <span class="foreshadow-stat-num">{{ foreshadowStats.planted }}</span>
              <span class="foreshadow-stat-label">已埋设</span>
            </div>
            <div class="foreshadow-stat">
              <span class="foreshadow-stat-num">{{ foreshadowStats.developing }}</span>
              <span class="foreshadow-stat-label">发展中</span>
            </div>
            <div class="foreshadow-stat">
              <span class="foreshadow-stat-num">{{ foreshadowStats.resolved }}</span>
              <span class="foreshadow-stat-label">已回收</span>
            </div>
          </div>
          <div v-if="foreshadowLoading" class="empty-text">加载中…</div>
          <div v-else-if="foreshadowError" class="empty-text">加载失败：{{ foreshadowError }}</div>
          <div v-else-if="foreshadowList.length === 0" class="empty-text">暂无伏笔条目</div>
          <div v-else class="foreshadow-list-mini">
            <div v-for="f in foreshadowList" :key="f.id" class="foreshadow-mini-card">
              <span class="foreshadow-mini-title">{{ f.title }}</span>
              <span class="foreshadow-mini-status" :class="`status-${f.status}`">{{
                foreshadowStatusMap[f.status] || f.status
              }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 故事演进 -->
      <div v-show="activeTab === 'evolution'" class="tab-content">
        <div class="section">
          <div class="section-header-static">
            <TrendingUp class="section-icon" />
            <span class="section-title-text">历史版本</span>
          </div>
          <div class="snapshot-stats">
            <span class="snapshot-stat">{{ snapshotList.length }} 个快照</span>
          </div>
          <div v-if="snapshotLoading" class="empty-text">加载中…</div>
          <div v-else-if="snapshotError" class="empty-text">加载失败：{{ snapshotError }}</div>
          <p v-else-if="snapshotList.length === 0" class="empty-text">暂无历史版本</p>
          <div v-else class="snapshot-list">
            <div v-for="s in snapshotList" :key="s.id" class="snapshot-card">
              <div class="snapshot-card-head">
                <span class="snapshot-name">{{ s.name }}</span>
                <span class="snapshot-type-tag">{{
                  snapshotTypeMap[s.snapshot_type] || s.snapshot_type
                }}</span>
              </div>
              <p v-if="s.description" class="snapshot-desc">{{ s.description }}</p>
              <div class="snapshot-meta">
                <span class="snapshot-time">{{ formatSnapshotTime(s.created_at) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Bible -->
      <div v-show="activeTab === 'bible'" class="tab-content">
        <div class="section">
          <div class="section-header-static">
            <Book class="section-icon" />
            <span class="section-title-text">设定</span>
          </div>
          <div class="bible-stats">
            <span class="bible-stat">{{ bibleStats.characters }} 角色</span>
            <span class="bible-stat">{{ bibleStats.locations }} 地点</span>
            <span class="bible-stat">{{ bibleStats.items }} 物品</span>
          </div>
          <div v-if="bibleLoading" class="empty-text">加载中…</div>
          <div v-else-if="bibleError" class="empty-text">加载失败：{{ bibleError }}</div>
          <div
            v-else-if="bibleCharacters.length === 0 && bibleSettings.length === 0"
            class="empty-text"
          >
            暂无设定
          </div>
          <div v-else class="bible-list">
            <div v-for="c in bibleCharacters" :key="`c-${c.id}`" class="bible-card">
              <span class="bible-type type-character">角色</span>
              <span class="bible-name">{{ c.name }}</span>
            </div>
            <div v-for="s in bibleSettings" :key="`s-${s.id}`" class="bible-card">
              <span class="bible-type" :class="`type-${s.setting_type}`">{{
                settingTypeMap[s.setting_type] || s.setting_type
              }}</span>
              <span class="bible-name">{{ s.name }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 知识库 -->
      <div v-show="activeTab === 'knowledge'" class="tab-content">
        <div class="section">
          <div class="section-header-static">
            <Ban class="section-icon" />
            <span class="section-title-text">知识库</span>
          </div>
          <div class="knowledge-stats">
            <span class="knowledge-stat">{{ knowledgeTriples.length }} 三元组</span>
            <span class="knowledge-stat">{{ chapterSummaries.length }} 摘要</span>
          </div>
          <div v-if="knowledgeLoading" class="empty-text">加载中…</div>
          <div v-else-if="knowledgeError" class="empty-text">加载失败：{{ knowledgeError }}</div>
          <p v-else-if="knowledgeTriples.length === 0" class="empty-text">暂无知识条目</p>
          <div v-else class="knowledge-list">
            <div v-for="t in knowledgeTriples" :key="t.id" class="knowledge-card">
              <span class="triple-subject">{{ t.subject }}</span>
              <span class="triple-predicate">{{ t.predicate }}</span>
              <span class="triple-object">{{ t.object }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 角色档案 -->
      <div v-show="activeTab === 'characters'" class="tab-content">
        <div class="section">
          <div class="section-header-static">
            <Users class="section-icon" />
            <span class="section-title-text">角色档案</span>
          </div>
          <div v-if="charactersLoading" class="empty-text">加载中…</div>
          <div v-else-if="charactersError" class="empty-text">加载失败：{{ charactersError }}</div>
          <p v-else-if="charactersList.length === 0" class="empty-text">暂无角色</p>
          <div v-else class="character-list-mini">
            <div v-for="c in charactersList" :key="c.id" class="character-mini-card">
              <div class="char-mini-avatar">{{ c.name.slice(0, 1) }}</div>
              <div class="char-mini-info">
                <span class="char-mini-name">{{ c.name }}</span>
                <span class="char-mini-desc">{{ c.role || c.description || '—' }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- 手稿道具 -->
      <div v-show="activeTab === 'manuscript'" class="tab-content">
        <div class="section">
          <div class="section-header-static">
            <Package class="section-icon" />
            <span class="section-title-text">手稿道具</span>
          </div>
          <p class="empty-text">暂无道具</p>
        </div>
      </div>

      <!-- 世界观 -->
      <div v-show="activeTab === 'worldview'" class="tab-content">
        <div class="section">
          <div class="section-header-static">
            <Globe class="section-icon" />
            <span class="section-title-text">世界观</span>
          </div>
          <div v-if="worldviewLoading" class="empty-text">加载中…</div>
          <div v-else-if="worldviewError" class="empty-text">加载失败：{{ worldviewError }}</div>
          <p v-else-if="worldviewList.length === 0" class="empty-text">暂无世界观设定</p>
          <div v-else class="worldview-list">
            <div v-for="w in worldviewList" :key="w.id" class="worldview-card">
              <div class="worldview-name">{{ w.name }}</div>
              <p v-if="w.description" class="worldview-desc">{{ w.description }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import {
  ChevronDown,
  ChevronRight,
  FileText,
  Users,
  MapPin,
  AlertTriangle,
  Bookmark,
  TrendingUp,
  Book,
  Ban,
  Package,
  Globe,
} from '@vicons/tabler'
import { getForeshadowList, getPendingReport, type Foreshadow, type PendingReport } from '@/api/foreshadows'
import {
  getKnowledgeTriples,
  getChapterSummaries,
  type KnowledgeTriple,
  type ChapterSummary,
} from '@/api/knowledge'
import { listSnapshots, type Snapshot } from '@/api/snapshots'
import {
  getIronLock,
  getMemoryFacts,
  getMemoryBeats,
  type IronLockData,
  type MemoryFact,
  type MemoryBeat,
} from '@/api/memory'
import { getCharacterList, getSettingList, type Character, type WorldSetting } from '@/api/bible'
import { useCurrentNovelId } from '@/composables/useCurrentNovelId'
import { useRoute } from 'vue-router'
import { useChapterStore } from '@/stores/chapter'
import { getReview } from '@/api/review'

const { novelId } = useCurrentNovelId()
const route = useRoute()
const chapterStore = useChapterStore()

const tabs = [
  { key: 'briefing', label: '叙事简报' },
  { key: 'context', label: '当前语境' },
  { key: 'foreshadow', label: '伏笔账本' },
  { key: 'evolution', label: '故事演进' },
  { key: 'bible', label: '设定' },
  { key: 'worldview', label: '世界观' },
  { key: 'knowledge', label: '知识库' },
  { key: 'characters', label: '角色档案' },
  { key: 'manuscript', label: '手稿道具' },
]

const activeTab = ref('briefing')
const summaryExpanded = ref(true)

// ===== 伏笔账本 =====
const foreshadowLoading = ref(false)
const foreshadowError = ref('')
const foreshadowList = ref<Foreshadow[]>([])

// ===== 伏笔提醒（概览 tab，待回收伏笔摘要）=====
const pendingLoading = ref(false)
const pendingError = ref('')
const pendingReport = ref<PendingReport | null>(null)

async function fetchPendingReport() {
  if (!novelId.value) return
  pendingLoading.value = true
  pendingError.value = ''
  try {
    pendingReport.value = await getPendingReport(novelId.value)
  } catch (e: unknown) {
    pendingError.value = (e as Error)?.message || '加载伏笔提醒失败'
    pendingReport.value = null
  } finally {
    pendingLoading.value = false
  }
}

// ===== 综合质量评分（概览 tab，复用 getReview + tension_score 回退）=====
const qualityScore = ref(0)
const qualityLoading = ref(false)
const qualityError = ref('')
const reviewGrade = ref('')

// 圆环周长 = 2 * π * 52 ≈ 326.7
const RING_CIRCUMFERENCE = 326.7
const qualityDash = computed(() => {
  const s = Math.min(100, Math.max(0, qualityScore.value))
  const filled = (s / 100) * RING_CIRCUMFERENCE
  return `${filled.toFixed(2)} ${RING_CIRCUMFERENCE.toFixed(2)}`
})

async function fetchQuality() {
  const chapterId = route.params.chapterId as string | undefined
  if (!chapterId) {
    qualityScore.value = 0
    reviewGrade.value = ''
    return
  }
  qualityLoading.value = true
  qualityError.value = ''
  try {
    const review = await getReview(chapterId)
    if (review && typeof review.total_score === 'number') {
      qualityScore.value = Math.round(review.total_score)
      reviewGrade.value = review.grade || ''
    } else if (
      chapterStore.currentChapter?.tension_score &&
      chapterStore.currentChapter.tension_score !== 50.0
    ) {
      // 回退到 chapter.tension_score（默认 50.0 视为未评分）
      qualityScore.value = Math.round(chapterStore.currentChapter.tension_score)
      reviewGrade.value = ''
    } else {
      qualityScore.value = 0
      reviewGrade.value = ''
    }
  } catch (e: unknown) {
    qualityError.value = (e as Error)?.message || '加载评分失败'
    qualityScore.value = 0
  } finally {
    qualityLoading.value = false
  }
}

const foreshadowStatusMap: Record<string, string> = {
  planted: '已埋设',
  developing: '发展中',
  resolved: '已回收',
  forgotten: '被遗忘',
}

const foreshadowStats = computed(() => {
  const list = foreshadowList.value
  return {
    planted: list.filter((f) => f.status === 'planted').length,
    developing: list.filter((f) => f.status === 'developing').length,
    resolved: list.filter((f) => f.status === 'resolved').length,
  }
})

async function fetchForeshadows() {
  if (!novelId.value) return
  foreshadowLoading.value = true
  foreshadowError.value = ''
  try {
    const res = await getForeshadowList(novelId.value)
    foreshadowList.value = res || []
  } catch (e: unknown) {
    foreshadowError.value = (e as Error)?.message || '加载伏笔失败'
    foreshadowList.value = []
  } finally {
    foreshadowLoading.value = false
  }
}

// ===== 知识库 =====
const knowledgeLoading = ref(false)
const knowledgeError = ref('')
const knowledgeTriples = ref<KnowledgeTriple[]>([])
const chapterSummaries = ref<ChapterSummary[]>([])

async function fetchKnowledge() {
  if (!novelId.value) return
  knowledgeLoading.value = true
  knowledgeError.value = ''
  try {
    const [triples, summaries] = await Promise.all([
      getKnowledgeTriples(novelId.value),
      getChapterSummaries(novelId.value),
    ])
    knowledgeTriples.value = triples || []
    chapterSummaries.value = summaries || []
  } catch (e: unknown) {
    knowledgeError.value = (e as Error)?.message || '加载知识库失败'
    knowledgeTriples.value = []
    chapterSummaries.value = []
  } finally {
    knowledgeLoading.value = false
  }
}

// ===== 故事演进（历史快照） =====
const snapshotLoading = ref(false)
const snapshotError = ref('')
const snapshotList = ref<Snapshot[]>([])

const snapshotTypeMap: Record<string, string> = {
  manual: '手动',
  auto: '自动',
  chapter: '章节',
  milestone: '里程碑',
}

function formatSnapshotTime(iso: string): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

async function fetchSnapshots() {
  if (!novelId.value) return
  snapshotLoading.value = true
  snapshotError.value = ''
  try {
    const res = await listSnapshots(novelId.value)
    snapshotList.value = res || []
  } catch (e: unknown) {
    snapshotError.value = (e as Error)?.message || '加载历史版本失败'
    snapshotList.value = []
  } finally {
    snapshotLoading.value = false
  }
}

// ===== 叙事简报 =====
const briefingLoading = ref(false)
const briefingError = ref('')
const ironLock = ref<IronLockData | null>(null)
const memoryFacts = ref<MemoryFact[]>([])

async function fetchBriefing() {
  if (!novelId.value) return
  briefingLoading.value = true
  briefingError.value = ''
  try {
    const [lock, facts] = await Promise.all([
      getIronLock(novelId.value),
      getMemoryFacts(novelId.value),
    ])
    ironLock.value = lock || null
    memoryFacts.value = facts || []
  } catch (e: unknown) {
    briefingError.value = (e as Error)?.message || '加载叙事简报失败'
    ironLock.value = null
    memoryFacts.value = []
  } finally {
    briefingLoading.value = false
  }
}

// ===== 当前语境 =====
const contextLoading = ref(false)
const contextError = ref('')
const memoryBeats = ref<MemoryBeat[]>([])
// 在场人物 / 地点物品（context tab，复用已 import 的 getCharacterList / getSettingList）
const sceneCharacters = ref<Character[]>([])
const sceneSettings = ref<WorldSetting[]>([])

const beatTypeMap: Record<string, string> = {
  opening: '开篇',
  rising: '上升',
  climax: '高潮',
  falling: '回落',
  resolution: '收束',
  turning: '转折',
  foreshadow: '伏笔',
  callback: '回收',
}

async function fetchContext() {
  if (!novelId.value) return
  contextLoading.value = true
  contextError.value = ''
  try {
    const [beats, chars, settings] = await Promise.all([
      getMemoryBeats(novelId.value),
      getCharacterList(novelId.value),
      getSettingList(novelId.value),
    ])
    memoryBeats.value = beats || []
    sceneCharacters.value = chars || []
    // 筛选地点 / 物品类型设定
    sceneSettings.value = (settings || []).filter(
      (s) => s.setting_type === 'location' || s.setting_type === 'item'
    )
  } catch (e: unknown) {
    contextError.value = (e as Error)?.message || '加载当前语境失败'
    memoryBeats.value = []
    sceneCharacters.value = []
    sceneSettings.value = []
  } finally {
    contextLoading.value = false
  }
}

// ===== Bible =====
const bibleLoading = ref(false)
const bibleError = ref('')
const bibleCharacters = ref<Character[]>([])
const bibleSettings = ref<WorldSetting[]>([])

const settingTypeMap: Record<string, string> = {
  world: '世界',
  worldview: '世界观',
  location: '地点',
  item: '物品',
  faction: '势力',
  system: '体系',
  history: '历史',
}

const bibleStats = computed(() => ({
  characters: bibleCharacters.value.length,
  locations: bibleSettings.value.filter((s) => s.setting_type === 'location').length,
  items: bibleSettings.value.filter((s) => s.setting_type === 'item').length,
}))

async function fetchBible() {
  if (!novelId.value) return
  bibleLoading.value = true
  bibleError.value = ''
  try {
    const [chars, settings] = await Promise.all([
      getCharacterList(novelId.value),
      getSettingList(novelId.value),
    ])
    bibleCharacters.value = chars || []
    bibleSettings.value = settings || []
  } catch (e: unknown) {
    bibleError.value = (e as Error)?.message || '加载设定失败'
    bibleCharacters.value = []
    bibleSettings.value = []
  } finally {
    bibleLoading.value = false
  }
}

// ===== 角色档案 =====
const charactersLoading = ref(false)
const charactersError = ref('')
const charactersList = ref<Character[]>([])

async function fetchCharacters() {
  if (!novelId.value) return
  charactersLoading.value = true
  charactersError.value = ''
  try {
    const res = await getCharacterList(novelId.value)
    charactersList.value = res || []
  } catch (e: unknown) {
    charactersError.value = (e as Error)?.message || '加载角色档案失败'
    charactersList.value = []
  } finally {
    charactersLoading.value = false
  }
}

// ===== 世界观 =====
const worldviewLoading = ref(false)
const worldviewError = ref('')
const worldviewList = ref<WorldSetting[]>([])

async function fetchWorldview() {
  if (!novelId.value) return
  worldviewLoading.value = true
  worldviewError.value = ''
  try {
    const res = await getSettingList(novelId.value)
    const list = res || []
    worldviewList.value = list.filter(
      (s) => s.setting_type === 'world' || s.setting_type === 'worldview'
    )
  } catch (e: unknown) {
    worldviewError.value = (e as Error)?.message || '加载世界观失败'
    worldviewList.value = []
  } finally {
    worldviewLoading.value = false
  }
}

onMounted(() => {
  if (activeTab.value === 'briefing') {
    fetchBriefing()
    fetchQuality()
  }
  else if (activeTab.value === 'context') {
    fetchContext()
    fetchPendingReport()
  }
  else if (activeTab.value === 'knowledge') fetchKnowledge()
  else if (activeTab.value === 'foreshadow') fetchForeshadows()
  else if (activeTab.value === 'evolution') fetchSnapshots()
  else if (activeTab.value === 'bible') fetchBible()
  else if (activeTab.value === 'characters') fetchCharacters()
  else if (activeTab.value === 'worldview') fetchWorldview()
})

watch(activeTab, (tab) => {
  if (tab === 'briefing') {
    fetchBriefing()
    fetchQuality()
  }
  else if (tab === 'context') {
    fetchContext()
    fetchPendingReport()
  }
  else if (tab === 'knowledge') fetchKnowledge()
  else if (tab === 'foreshadow') fetchForeshadows()
  else if (tab === 'evolution') fetchSnapshots()
  else if (tab === 'bible') fetchBible()
  else if (tab === 'characters') fetchCharacters()
  else if (tab === 'worldview') fetchWorldview()
})

// 切换章节时刷新评分
watch(
  () => route.params.chapterId,
  () => {
    if (activeTab.value === 'briefing') fetchQuality()
  }
)
</script>

<style scoped>
.context-panel {
  width: 320px;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--xy-surface-1);
  font-family: var(--xy-font-sans);
  overflow: hidden;
}

/* ========== 标签栏 ========== */
.tab-bar {
  flex-shrink: 0;
  height: var(--xy-panel-header-h);
  border-bottom: var(--xy-border-w-1) solid var(--xy-border-1);
  overflow: hidden;
}

.tab-scroll {
  display: flex;
  align-items: stretch;
  height: 100%;
  overflow-x: auto;
  overflow-y: hidden;
  padding: 0 var(--xy-space-3);
  scrollbar-width: none;
}

.tab-scroll::-webkit-scrollbar {
  display: none;
}

.tab-item {
  flex-shrink: 0;
  height: 100%;
  padding: 0 var(--xy-space-2);
  border: none;
  background: transparent;
  color: var(--xy-text-3);
  font-size: var(--xy-fs-sm);
  font-weight: var(--xy-fw-reg);
  cursor: pointer;
  white-space: nowrap;
  position: relative;
  transition: color 150ms ease;
}

.tab-item:hover {
  color: var(--xy-text-2);
}

.tab-active {
  color: var(--xy-brand-600);
  font-weight: var(--xy-fw-med);
}

.tab-active::after {
  content: '';
  position: absolute;
  left: var(--xy-space-2);
  right: var(--xy-space-2);
  bottom: 0;
  height: 2px;
  background: var(--xy-brand-500);
  border-radius: 1px 1px 0 0;
}

/* ========== 内容区 ========== */
.panel-content {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: var(--xy-space-3);
}

.panel-content::-webkit-scrollbar {
  width: 6px;
}

.panel-content::-webkit-scrollbar-track {
  background: transparent;
}

.panel-content::-webkit-scrollbar-thumb {
  background: rgba(124, 108, 191, 0.2);
  border-radius: 3px;
}

.tab-content {
  display: flex;
  flex-direction: column;
  gap: var(--xy-space-3);
}

.tab-placeholder {
  justify-content: center;
  align-items: center;
  padding-top: var(--xy-space-16);
}

.placeholder-text {
  text-align: center;
  color: var(--xy-text-3);
  font-size: var(--xy-fs-sm);
}

.placeholder-text span {
  display: block;
  color: var(--xy-text-2);
  font-weight: var(--xy-fw-med);
  margin-bottom: var(--xy-space-2);
}

.placeholder-text p {
  margin: 0;
  font-size: var(--xy-fs-xs);
}

.empty-text {
  margin: 0;
  padding: var(--xy-space-3);
  text-align: center;
  color: var(--xy-text-4);
  font-size: var(--xy-fs-xs);
}

/* ========== 综合质量评分卡片 ========== */
.quality-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--xy-space-4);
  border-radius: var(--xy-radius-lg);
  background: var(--xy-surface-2);
  border: var(--xy-border-w-1) solid var(--xy-border-1);
}

.card-title {
  font-size: var(--xy-fs-sm);
  font-weight: var(--xy-fw-sb);
  color: var(--xy-text-2);
  margin-bottom: var(--xy-space-3);
  align-self: flex-start;
}

.quality-ring-wrap {
  position: relative;
  width: 120px;
  height: 120px;
  margin-bottom: var(--xy-space-3);
}

.quality-ring {
  width: 100%;
  height: 100%;
}

.quality-score {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  align-items: baseline;
  gap: 2px;
}

.score-num {
  font-size: var(--xy-fs-3xl);
  font-weight: var(--xy-fw-bold);
  color: var(--xy-brand-600);
  font-variant-numeric: tabular-nums;
  line-height: 1;
}

.score-unit {
  font-size: var(--xy-fs-sm);
  color: var(--xy-text-3);
}

.quality-tag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 2px 10px;
  border-radius: var(--xy-radius-full);
  background: var(--xy-brand-100);
  color: var(--xy-brand-600);
  font-size: var(--xy-fs-xs);
  font-weight: var(--xy-fw-med);
  margin-bottom: var(--xy-space-2);
}

.quality-desc {
  font-size: var(--xy-fs-xs);
  color: var(--xy-text-3);
  text-align: center;
}

/* ========== 通用 section ========== */
.section {
  display: flex;
  flex-direction: column;
  gap: var(--xy-space-2);
}

.section-title {
  font-size: var(--xy-fs-sm);
  font-weight: var(--xy-fw-sb);
  color: var(--xy-text-2);
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--xy-space-1);
  border: none;
  background: transparent;
  cursor: pointer;
  width: 100%;
  text-align: left;
}

.section-header-static {
  display: flex;
  align-items: center;
  gap: var(--xy-space-1_5);
  padding: var(--xy-space-1);
}

.section-title-left {
  display: flex;
  align-items: center;
  gap: var(--xy-space-1_5);
  font-size: var(--xy-fs-sm);
  font-weight: var(--xy-fw-sb);
  color: var(--xy-text-2);
}

.section-title-text {
  font-size: var(--xy-fs-sm);
  font-weight: var(--xy-fw-sb);
  color: var(--xy-text-2);
}

.section-icon {
  width: 14px;
  height: 14px;
  color: var(--xy-text-3);
  flex-shrink: 0;
}

.section-icon-warning {
  color: var(--xy-warning);
}

.chevron-icon {
  width: 12px;
  height: 12px;
  color: var(--xy-text-4);
  flex-shrink: 0;
  transition: transform 150ms ease;
}

/* ========== 故事线进度 ========== */
.progress-list {
  display: flex;
  flex-direction: column;
  gap: var(--xy-space-2);
}

.progress-item {
  display: flex;
  flex-direction: column;
  gap: var(--xy-space-1);
}

.progress-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.progress-label {
  font-size: var(--xy-fs-xs);
  color: var(--xy-text-3);
}

.progress-value {
  font-size: var(--xy-fs-xs);
  color: var(--xy-text-2);
  font-weight: var(--xy-fw-med);
  font-variant-numeric: tabular-nums;
}

.progress-bar {
  height: 6px;
  border-radius: var(--xy-radius-full);
  background: var(--xy-surface-2);
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: var(--xy-radius-full);
  transition: width 300ms ease;
}

.progress-main {
  background: var(--xy-brand-500);
}

.progress-sub {
  background: var(--xy-info);
}

.progress-romance {
  background: var(--xy-text-4);
}

.foreshadow-item {
  display: flex;
  align-items: center;
  gap: var(--xy-space-1_5);
  margin-top: var(--xy-space-1);
}

.foreshadow-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--xy-warning);
  box-shadow: 0 0 0 3px rgba(251, 191, 36, 0.15);
}

.foreshadow-text {
  font-size: var(--xy-fs-xs);
  color: var(--xy-text-3);
}

/* ========== 当前视角 ========== */
.pov-tabs {
  display: flex;
  gap: var(--xy-space-2);
}

.pov-btn {
  padding: 6px 16px;
  border-radius: var(--xy-radius-md);
  border: var(--xy-border-w-1) solid var(--xy-border-1);
  background: var(--xy-surface-2);
  color: var(--xy-text-3);
  font-size: var(--xy-fs-sm);
  font-weight: var(--xy-fw-med);
  cursor: pointer;
  transition: all 150ms ease;
}

.pov-btn:hover {
  color: var(--xy-text-2);
}

.pov-active {
  background: var(--xy-brand-500);
  border-color: var(--xy-brand-500);
  color: var(--xy-text-inverse);
}

/* ========== AI建议 ========== */
.suggestion-list {
  display: flex;
  flex-direction: column;
  gap: var(--xy-space-2);
}

.suggestion-card {
  display: flex;
  gap: var(--xy-space-2_5);
  padding: var(--xy-space-3);
  border-radius: var(--xy-radius-md);
  background: var(--xy-surface-2);
  border: var(--xy-border-w-1) solid var(--xy-border-1);
}

.suggestion-icon {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  border-radius: var(--xy-radius-sm);
  background: var(--xy-warning-bg);
  display: flex;
  align-items: center;
  justify-content: center;
}

.bulb-icon {
  width: 14px;
  height: 14px;
  color: var(--xy-warning);
}

.suggestion-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: var(--xy-space-2);
}

.suggestion-text {
  margin: 0;
  font-size: var(--xy-fs-xs);
  color: var(--xy-text-2);
  line-height: var(--xy-lh-relaxed);
}

.suggestion-actions {
  display: flex;
  gap: var(--xy-space-2);
}

.action-btn {
  padding: 4px 12px;
  border-radius: var(--xy-radius-sm);
  border: none;
  font-size: var(--xy-fs-xs);
  font-weight: var(--xy-fw-med);
  cursor: pointer;
  transition: all 150ms ease;
}

.action-accept {
  background: var(--xy-brand-500);
  color: var(--xy-text-inverse);
}

.action-accept:hover {
  background: var(--xy-brand-400);
}

.action-ignore {
  background: var(--xy-surface-1);
  color: var(--xy-text-3);
}

.action-ignore:hover {
  color: var(--xy-text-2);
  background: var(--xy-surface-hover);
}

/* ========== 前文摘要 ========== */
.summary-list {
  display: flex;
  flex-direction: column;
  gap: var(--xy-space-2);
}

.summary-card {
  padding: var(--xy-space-2) var(--xy-space-2_5);
  border-radius: var(--xy-radius-md);
  background: var(--xy-surface-2);
}

.summary-chapter {
  font-size: var(--xy-fs-sm);
  font-weight: var(--xy-fw-med);
  color: var(--xy-text-2);
  margin-bottom: var(--xy-space-1);
}

.summary-text {
  margin: 0;
  font-size: var(--xy-fs-xs);
  color: var(--xy-text-3);
  line-height: var(--xy-lh-relaxed);
}

/* ========== 在场人物 ========== */
.character-list {
  display: flex;
  flex-direction: column;
  gap: var(--xy-space-2);
}

.character-card {
  display: flex;
  align-items: center;
  gap: var(--xy-space-2_5);
  padding: var(--xy-space-2_5);
  border-radius: var(--xy-radius-md);
  background: var(--xy-surface-2);
  min-height: 48px;
}

.char-avatar {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  border-radius: var(--xy-radius-full);
  background: var(--xy-brand-200);
  color: var(--xy-brand-600);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--xy-fs-xs);
  font-weight: var(--xy-fw-sb);
}

.char-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.char-name-row {
  display: flex;
  align-items: center;
  gap: var(--xy-space-1_5);
}

.char-name {
  font-size: var(--xy-fs-sm);
  font-weight: var(--xy-fw-med);
  color: var(--xy-text-1);
}

.char-role {
  display: inline-flex;
  align-items: center;
  padding: 1px 6px;
  border-radius: 2px;
  font-size: 9px;
  font-weight: var(--xy-fw-med);
  line-height: 1;
}

.role-main {
  background: var(--xy-info-bg);
  color: var(--xy-info);
}

.role-support {
  background: var(--xy-surface-active);
  color: var(--xy-text-3);
}

.char-status {
  font-size: var(--xy-fs-xs);
  color: var(--xy-text-3);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ========== 地点与物品标签 ========== */
.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--xy-space-1_5);
}

.tag-item {
  display: inline-flex;
  align-items: center;
  padding: 3px 8px;
  border-radius: var(--xy-radius-sm);
  background: var(--xy-surface-2);
  color: var(--xy-text-2);
  font-size: var(--xy-fs-xs);
  white-space: nowrap;
}

/* ========== 伏笔提醒 ========== */
.foreshadow-warning {
  display: flex;
  align-items: flex-start;
  gap: var(--xy-space-2);
  padding: var(--xy-space-2_5);
  border-radius: var(--xy-radius-md);
  background: var(--xy-warning-bg);
  border: var(--xy-border-w-1) solid rgba(251, 191, 36, 0.15);
}

.warning-icon {
  flex-shrink: 0;
  width: 14px;
  height: 14px;
  color: var(--xy-warning);
  margin-top: 1px;
}

.warning-body {
  flex: 1;
  min-width: 0;
}

.warning-title {
  font-size: var(--xy-fs-sm);
  font-weight: var(--xy-fw-med);
  color: var(--xy-warning);
  margin-bottom: 2px;
}

.warning-text {
  margin: 0;
  font-size: var(--xy-fs-xs);
  color: var(--xy-text-3);
  line-height: var(--xy-lh-relaxed);
}

/* ========== 伏笔账本 ========== */
.foreshadow-stats {
  display: flex;
  gap: var(--xy-space-2);
  margin-bottom: var(--xy-space-2);
}

.foreshadow-stat {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: var(--xy-space-2);
  background: var(--xy-surface-2);
  border-radius: var(--xy-radius-sm);
}

.foreshadow-stat-num {
  font-size: var(--xy-fs-lg);
  font-weight: var(--xy-fw-bold);
  color: var(--xy-brand-500);
}

.foreshadow-stat-label {
  font-size: var(--xy-fs-xs);
  color: var(--xy-text-3);
}

.foreshadow-list-mini {
  display: flex;
  flex-direction: column;
  gap: var(--xy-space-1);
}

.foreshadow-mini-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--xy-space-1_5);
  background: var(--xy-surface-2);
  border-radius: var(--xy-radius-sm);
}

.foreshadow-mini-title {
  font-size: var(--xy-fs-xs);
  color: var(--xy-text-2);
}

.foreshadow-mini-status {
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 3px;
}

.foreshadow-mini-status.status-planted {
  background: color-mix(in srgb, var(--xy-info) 20%, transparent);
  color: var(--xy-info);
}

.foreshadow-mini-status.status-developing {
  background: color-mix(in srgb, var(--xy-warning) 20%, transparent);
  color: var(--xy-warning);
}

/* ========== 故事演进 ========== */
.evolution-list {
  display: flex;
  flex-direction: column;
  gap: var(--xy-space-2);
}

.evolution-item {
  display: flex;
  gap: var(--xy-space-2);
}

.evolution-step {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--xy-brand-500);
  display: flex;
  align-items: center;
  justify-content: center;
}

.step-num {
  font-size: 10px;
  color: var(--xy-text-inverse);
  font-weight: var(--xy-fw-med);
}

.evolution-content {
  flex: 1;
  min-width: 0;
}

.evolution-title {
  font-size: var(--xy-fs-sm);
  font-weight: var(--xy-fw-med);
  color: var(--xy-text-1);
}

.evolution-desc {
  margin: 0;
  font-size: var(--xy-fs-xs);
  color: var(--xy-text-3);
  line-height: var(--xy-lh-relaxed);
}

/* ========== 历史版本（故事演进） ========== */
.snapshot-stats {
  display: flex;
  gap: var(--xy-space-2);
  margin-bottom: var(--xy-space-2);
}

.snapshot-stat {
  font-size: var(--xy-fs-xs);
  color: var(--xy-text-3);
}

.snapshot-list {
  display: flex;
  flex-direction: column;
  gap: var(--xy-space-1_5);
}

.snapshot-card {
  display: flex;
  flex-direction: column;
  gap: var(--xy-space-1);
  padding: var(--xy-space-2);
  background: var(--xy-surface-2);
  border-radius: var(--xy-radius-sm);
  border-left: 2px solid var(--xy-brand-500);
}

.snapshot-card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--xy-space-2);
}

.snapshot-name {
  font-size: var(--xy-fs-xs);
  font-weight: var(--xy-fw-med);
  color: var(--xy-text-1);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
  min-width: 0;
}

.snapshot-type-tag {
  flex-shrink: 0;
  font-size: 10px;
  padding: 1px 6px;
  border-radius: 3px;
  background: color-mix(in srgb, var(--xy-brand-500) 18%, transparent);
  color: var(--xy-brand-600);
}

.snapshot-desc {
  margin: 0;
  font-size: 10px;
  color: var(--xy-text-3);
  line-height: var(--xy-lh-relaxed);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.snapshot-meta {
  display: flex;
  align-items: center;
  gap: var(--xy-space-1_5);
}

.snapshot-time {
  font-size: 10px;
  color: var(--xy-text-4);
  font-variant-numeric: tabular-nums;
}

/* ========== Bible ========== */
.bible-stats {
  display: flex;
  gap: var(--xy-space-2);
  margin-bottom: var(--xy-space-2);
}

.bible-stat {
  font-size: var(--xy-fs-xs);
  color: var(--xy-text-3);
}

.bible-list {
  display: flex;
  flex-direction: column;
  gap: var(--xy-space-1);
}

.bible-card {
  display: flex;
  align-items: center;
  gap: var(--xy-space-2);
  padding: var(--xy-space-1_5);
  background: var(--xy-surface-2);
  border-radius: var(--xy-radius-sm);
}

.bible-type {
  font-size: 9px;
  padding: 1px 6px;
  border-radius: 3px;
}

.bible-type.type-character {
  background: color-mix(in srgb, var(--xy-info) 20%, transparent);
  color: var(--xy-info);
}

.bible-type.type-location {
  background: color-mix(in srgb, var(--xy-info) 20%, transparent);
  color: var(--xy-info);
}

.bible-type.type-item {
  background: color-mix(in srgb, var(--xy-purple) 20%, transparent);
  color: var(--xy-purple);
}

.bible-name {
  font-size: var(--xy-fs-xs);
  color: var(--xy-text-2);
}

/* ========== 知识库 ========== */
.knowledge-stats {
  display: flex;
  gap: var(--xy-space-2);
  margin-bottom: var(--xy-space-2);
}

.knowledge-stat {
  font-size: var(--xy-fs-xs);
  color: var(--xy-text-3);
}

.knowledge-list {
  display: flex;
  flex-direction: column;
  gap: var(--xy-space-1);
}

.knowledge-card {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: var(--xy-space-1_5);
  background: var(--xy-surface-2);
  border-radius: var(--xy-radius-sm);
  font-size: var(--xy-fs-xs);
}

.triple-subject {
  color: var(--xy-brand-600);
  font-weight: var(--xy-fw-med);
}

.triple-predicate {
  color: var(--xy-text-4);
}

.triple-object {
  color: var(--xy-text-2);
}

/* ========== 角色档案 ========== */
.character-list-mini {
  display: flex;
  flex-direction: column;
  gap: var(--xy-space-1);
}

.character-mini-card {
  display: flex;
  align-items: center;
  gap: var(--xy-space-2);
  padding: var(--xy-space-1_5);
  background: var(--xy-surface-2);
  border-radius: var(--xy-radius-sm);
}

.char-mini-avatar {
  width: 24px;
  height: 24px;
  border-radius: 50%;
  background: var(--xy-brand-200);
  color: var(--xy-brand-600);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 10px;
  font-weight: var(--xy-fw-sb);
}

.char-mini-info {
  flex: 1;
  min-width: 0;
}

.char-mini-name {
  font-size: var(--xy-fs-xs);
  font-weight: var(--xy-fw-med);
  color: var(--xy-text-1);
}

.char-mini-desc {
  font-size: 10px;
  color: var(--xy-text-4);
}

.char-mini-role {
  display: block;
  font-size: 10px;
  color: var(--xy-text-3);
  margin-top: 2px;
}

/* 地点与物品 mini 列表（context tab） */
.setting-list-mini {
  display: flex;
  flex-direction: column;
  gap: var(--xy-space-1);
}

.setting-mini-card {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--xy-space-2);
  padding: var(--xy-space-1_5);
  background: var(--xy-surface-2);
  border-radius: var(--xy-radius-sm);
}

.setting-mini-name {
  font-size: var(--xy-fs-xs);
  font-weight: var(--xy-fw-med);
  color: var(--xy-text-1);
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.setting-mini-cat {
  font-size: 10px;
  color: var(--xy-text-3);
  padding: 1px 6px;
  background: var(--xy-surface-3);
  border-radius: var(--xy-radius-sm);
  flex-shrink: 0;
}

/* ========== 手稿道具 ========== */
.manuscript-list {
  display: flex;
  flex-direction: column;
  gap: var(--xy-space-1);
}

.manuscript-card {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: var(--xy-space-1_5);
  background: var(--xy-surface-2);
  border-radius: var(--xy-radius-sm);
}

.manuscript-name {
  font-size: var(--xy-fs-xs);
  color: var(--xy-text-2);
}

.manuscript-type {
  font-size: 10px;
  color: var(--xy-text-4);
}

/* ========== 世界观 ========== */
.worldview-list {
  display: flex;
  flex-direction: column;
  gap: var(--xy-space-1);
}

.worldview-card {
  padding: var(--xy-space-1_5);
  background: var(--xy-surface-2);
  border-radius: var(--xy-radius-sm);
}

.worldview-name {
  font-size: var(--xy-fs-xs);
  font-weight: var(--xy-fw-med);
  color: var(--xy-text-1);
}

.worldview-desc {
  margin: 0;
  font-size: 10px;
  color: var(--xy-text-3);
  line-height: var(--xy-lh-relaxed);
}
</style>
