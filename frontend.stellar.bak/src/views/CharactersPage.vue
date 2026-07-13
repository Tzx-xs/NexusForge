<template>
  <div class="characters-page">
    <header class="topbar">
      <div class="topbar-left">
        <button class="back-home-btn" aria-label="返回首页" @click="router.push('/')">
          <ArrowLeft class="back-icon" />
          <span>返回首页</span>
        </button>
        <span class="brand-text">星渊笔</span>
        <span class="page-badge">人物</span>
      </div>
      <div class="topbar-right">
        <button class="icon-btn" aria-label="设置" @click="router.push('/settings')">
          <Settings class="icon" />
        </button>
        <div class="user-avatar">作</div>
      </div>
    </header>

    <main class="main-layout">
      <aside class="left-nav">
        <nav class="nav-list">
          <router-link to="/" class="nav-item">
            <Home class="nav-icon" />
          </router-link>
          <router-link to="/bible" class="nav-item">
            <Book class="nav-icon" />
          </router-link>
          <router-link to="/characters" class="nav-item nav-item-active">
            <Users class="nav-icon" />
          </router-link>
          <router-link to="/outline" class="nav-item">
            <ListDetails class="nav-icon" />
          </router-link>
          <router-link to="/review" class="nav-item">
            <Eye class="nav-icon" />
          </router-link>
          <router-link to="/settings" class="nav-item">
            <Settings class="nav-icon" />
          </router-link>
        </nav>
      </aside>

      <section class="content-area">
        <div class="toolbar">
          <div class="toolbar-left">
            <div class="search-box">
              <Search class="search-icon" />
              <input
                v-model="searchQuery"
                type="text"
                placeholder="搜索人物..."
                class="search-input"
              />
            </div>
          </div>
          <div class="filter-group">
            <button
              v-for="type in characterTypes"
              :key="type.value"
              class="filter-btn"
              :class="{ 'filter-btn-active': activeFilter === type.value }"
              @click="activeFilter = type.value"
            >
              {{ type.label }}
            </button>
          </div>
          <div class="sort-group">
            <ArrowsUpDown class="sort-icon" />
            <select v-model="sortBy" class="sort-select">
              <option value="freq">出场频率</option>
              <option value="time">创建时间</option>
            </select>
          </div>
          <button class="btn-new" @click="createNewCharacter">
            <Plus class="btn-icon" />
            <span>新建人物</span>
          </button>
        </div>

        <div class="page-header">
          <div class="title-wrap">
            <h1 class="page-title">人物管理</h1>
            <span class="count-badge">{{ filteredCharacters.length }}</span>
          </div>
        </div>

        <div class="character-grid">
          <article
            v-for="char in filteredCharacters"
            :key="char.id"
            class="character-card"
            :class="{ 'card-active': selectedCharacter?.id === char.id }"
            @click="selectCharacter(char)"
          >
            <div class="card-header">
              <div class="avatar" :style="{ background: char.avatarGradient }">
                {{ char.name.charAt(0) }}
              </div>
              <div class="char-info">
                <div class="name-row">
                  <span class="char-name">{{ char.name }}</span>
                  <span class="role-tag" :class="'role-' + char.role">
                    {{ char.roleLabel }}
                  </span>
                </div>
                <p class="char-desc">{{ char.description }}</p>
              </div>
            </div>
            <div class="tag-row">
              <span v-for="tag in char.tags" :key="tag" class="tag-item">
                {{ tag }}
              </span>
            </div>
            <div class="card-footer">
              <div class="radar-chart">
                <svg viewBox="0 0 100 100" width="72" height="72">
                  <polygon
                    points="50,10 93,35 80,83 20,83 7,35"
                    fill="none"
                    stroke="var(--xy-border-1)"
                    stroke-width="0.5"
                  />
                  <polygon
                    points="50,27 77,42 68,68 32,68 23,42"
                    fill="none"
                    stroke="var(--xy-border-1)"
                    stroke-width="0.5"
                  />
                  <polygon
                    points="50,44 62,52 57,66 43,66 38,52"
                    fill="none"
                    stroke="var(--xy-border-1)"
                    stroke-width="0.5"
                  />
                  <polygon
                    v-if="hasStatsData(char.stats)"
                    :points="getRadarPoints(char.stats)"
                    :fill="char.radarFill"
                    :stroke="char.radarStroke"
                    stroke-width="1"
                  />
                  <text
                    v-else
                    x="50"
                    y="52"
                    text-anchor="middle"
                    font-size="7"
                    fill="var(--xy-text-4)"
                  >
                    待补充
                  </text>
                </svg>
              </div>
            </div>
          </article>
        </div>

        <!-- 人物详情抽屉 -->
        <div v-if="selectedCharacter" class="detail-drawer">
          <div class="drawer-overlay" @click="closeDetail"></div>
          <div class="drawer-content">
            <div class="drawer-header">
              <div class="drawer-avatar" :style="{ background: selectedCharacter.avatarGradient }">
                {{ selectedCharacter.name.charAt(0) }}
              </div>
              <div class="drawer-title-group">
                <h2 class="drawer-title">{{ selectedCharacter.name }}</h2>
                <span class="role-tag" :class="'role-' + selectedCharacter.role">
                  {{ selectedCharacter.roleLabel }}
                </span>
              </div>
              <button class="drawer-close" @click="closeDetail">
                <X class="close-icon" />
              </button>
            </div>
            <div class="drawer-body">
              <div class="detail-section">
                <h3 class="section-title">人物简介</h3>
                <p v-if="selectedCharacter.description" class="section-content">
                  {{ selectedCharacter.description }}
                </p>
                <p v-else class="empty-tip">暂无简介，点击编辑补充</p>
              </div>
              <div class="detail-section">
                <h3 class="section-title">性格特征</h3>
                <p v-if="selectedCharacter.personality" class="section-content">
                  {{ selectedCharacter.personality }}
                </p>
                <p v-else class="empty-tip">暂无性格描述</p>
              </div>
              <div class="detail-section">
                <h3 class="section-title">人物背景</h3>
                <p v-if="selectedCharacter.background" class="section-content">
                  {{ selectedCharacter.background }}
                </p>
                <p v-else class="empty-tip">暂无背景信息</p>
              </div>
              <div class="detail-section">
                <h3 class="section-title">标签</h3>
                <div class="tag-row">
                  <span
                    v-for="tag in selectedCharacter.tags"
                    :key="tag"
                    class="tag-item tag-item-lg"
                  >
                    {{ tag }}
                  </span>
                </div>
              </div>
              <div class="detail-section">
                <h3 class="section-title">五维属性</h3>
                <div v-if="hasStatsData(selectedCharacter.stats)" class="stats-grid">
                  <div class="stat-item">
                    <span class="stat-label">力量</span>
                    <span class="stat-value">{{ selectedCharacter.stats.force }}</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">智慧</span>
                    <span class="stat-value">{{ selectedCharacter.stats.wisdom }}</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">魅力</span>
                    <span class="stat-value">{{ selectedCharacter.stats.charm }}</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">气运</span>
                    <span class="stat-value">{{ selectedCharacter.stats.luck }}</span>
                  </div>
                  <div class="stat-item">
                    <span class="stat-label">背景</span>
                    <span class="stat-value">{{ selectedCharacter.stats.background }}</span>
                  </div>
                </div>
                <p v-else class="empty-tip">角色档案待补充</p>
              </div>
              <div class="detail-section">
                <h3 class="section-title">基本信息</h3>
                <div class="info-list">
                  <div class="info-item">
                    <span class="info-label">出场章节</span>
                    <span
                      v-if="selectedCharacter.chapterAppearances?.length"
                      class="info-value"
                    >
                      {{ selectedCharacter.chapterAppearances.slice(0, 3).map(c => c.title).join('、') }}<span
                        v-if="selectedCharacter.chapterAppearances.length > 3"
                        class="more-hint"
                      >等 {{ selectedCharacter.chapterAppearances.length }} 章</span>
                    </span>
                    <span v-else class="info-value info-value-empty">暂无</span>
                  </div>
                  <div class="info-item">
                    <span class="info-label">关联人物</span>
                    <span
                      v-if="selectedCharacter.relations?.length"
                      class="info-value"
                    >
                      {{ selectedCharacter.relations.slice(0, 3).map(r => r.name).join('、') }}<span
                        v-if="selectedCharacter.relations.length > 3"
                        class="more-hint"
                      >等 {{ selectedCharacter.relations.length }} 人</span>
                    </span>
                    <span v-else class="info-value info-value-empty">暂无</span>
                  </div>
                </div>
              </div>
              <div class="drawer-actions">
                <button class="btn-edit" @click="openEditModal(selectedCharacter)">
                  <Pencil class="btn-icon" />
                  <span>编辑</span>
                </button>
                <button class="btn-delete" @click="handleDelete(selectedCharacter)">
                  <Trash class="btn-icon" />
                  <span>删除</span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>
    </main>

    <!-- 人物编辑弹窗 -->
    <n-modal
      v-model:show="editModalVisible"
      preset="card"
      title="编辑人物"
      style="width: 480px; max-width: 92vw"
    >
      <n-form :model="editForm" label-placement="top">
        <n-form-item label="姓名">
          <n-input v-model:value="editForm.name" placeholder="请输入姓名" />
        </n-form-item>
        <n-form-item label="角色类型">
          <n-select v-model:value="editForm.role" :options="roleOptions" />
        </n-form-item>
        <n-form-item label="性别">
          <n-select v-model:value="editForm.gender" :options="genderOptions" clearable placeholder="请选择性别" />
        </n-form-item>
        <n-form-item label="年龄">
          <n-input v-model:value="editForm.age" placeholder="请输入年龄" />
        </n-form-item>
        <n-form-item label="描述">
          <n-input
            v-model:value="editForm.description"
            type="textarea"
            :autosize="{ minRows: 2 }"
            placeholder="请输入描述"
          />
        </n-form-item>
        <n-form-item label="性格">
          <n-input
            v-model:value="editForm.personality"
            type="textarea"
            :autosize="{ minRows: 2 }"
            placeholder="请输入性格特征"
          />
        </n-form-item>
        <n-form-item label="背景">
          <n-input
            v-model:value="editForm.background"
            type="textarea"
            :autosize="{ minRows: 2 }"
            placeholder="请输入人物背景"
          />
        </n-form-item>
      </n-form>
      <template #footer>
        <div class="modal-footer">
          <n-button @click="editModalVisible = false">取消</n-button>
          <n-button type="primary" :loading="editSaving" @click="submitEdit">保存</n-button>
        </div>
      </template>
    </n-modal>

    <footer class="statusbar">
      <span class="status-text">人物管理 | 共 {{ characters.length }} 个角色</span>
    </footer>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NModal, NForm, NFormItem, NInput, NSelect } from 'naive-ui'
import { useBibleStore } from '@/stores/bible'
import { useNovelStore } from '@/stores/novel'
import { useCurrentNovelId } from '@/composables/useCurrentNovelId'
import { toast } from '@/utils/toast'
import {
  Home,
  Users,
  Pencil,
  Eye,
  Book,
  ListDetails,
  Settings,
  Search,
  Plus,
  ArrowsUpDown,
  X,
  ArrowLeft,
  Trash,
} from '@vicons/tabler'

interface ChapterAppearance {
  title: string
}

interface CharacterRelation {
  name: string
}

interface Character {
  id: number | string
  name: string
  role: 'protagonist' | 'supporting' | 'antagonist' | 'npc'
  roleLabel: string
  description: string
  personality: string
  background: string
  gender?: string
  age?: string
  tags: string[]
  avatarGradient: string
  radarFill: string
  radarStroke: string
  stats: {
    force: number
    wisdom: number
    charm: number
    luck: number
    background: number
  }
  chapterAppearances: ChapterAppearance[]
  relations: CharacterRelation[]
}

// 估算五维属性：基于 character 的 personality / background / description 真实字段
// 后端 character 表无五维字段，前端基于文本长度与关键词估算
function estimateStats(c: {
  personality?: string
  background?: string
  description?: string
  role: string
}): { force: number; wisdom: number; charm: number; luck: number; background: number } {
  const personality = c.personality || ''
  const bg = c.background || ''
  const desc = c.description || ''

  // 五维全无数据时返回全 0，由 UI 显示"角色档案待补充"
  if (!personality && !bg && !desc) {
    return { force: 0, wisdom: 0, charm: 0, luck: 0, background: 0 }
  }

  const allText = personality + bg + desc
  // 文本长度贡献：每 10 字 +5 分，上限 40
  const lenScore = (text: string) => Math.min(40, Math.floor(text.length / 10) * 5)

  const forceKw = ['力量', '强大', '坚毅', '热血', '勇', '武', '战斗', '强悍', '霸']
  const wisdomKw = ['智慧', '睿智', '冷静', '聪', '智', '谋', '算计', '深思']
  const charmKw = ['魅力', '英俊', '美丽', '迷人', '风度', '气质', '优雅']
  const luckKw = ['气运', '幸运', '命', '运', '机缘', '奇遇']

  const countKw = (text: string, kw: string[]) =>
    kw.reduce((s, k) => s + (text.includes(k) ? 1 : 0), 0)

  const role = mapRoleLabel(c.role)
  // 主角气运基础较高，反派次之
  const luckBase = role === 'protagonist' ? 50 : role === 'antagonist' ? 45 : 35

  return {
    force: Math.min(95, 30 + lenScore(personality) + countKw(allText, forceKw) * 8),
    wisdom: Math.min(95, 30 + lenScore(desc) + countKw(allText, wisdomKw) * 8),
    charm: Math.min(95, 30 + lenScore(personality) + countKw(allText, charmKw) * 8),
    luck: Math.min(95, luckBase + countKw(allText, luckKw) * 8),
    background: Math.min(95, 30 + lenScore(bg)),
  }
}

// 判断五维是否有有效数据
function hasStatsData(stats: Character['stats']): boolean {
  return (
    stats.force > 0 || stats.wisdom > 0 || stats.charm > 0 || stats.luck > 0 || stats.background > 0
  )
}

const router = useRouter()
const bibleStore = useBibleStore()
const novelStore = useNovelStore()
const { novelId } = useCurrentNovelId()

const searchQuery = ref('')
const activeFilter = ref('all')
const sortBy = ref('freq')
const selectedCharacter = ref<Character | null>(null)

const characterTypes = [
  { value: 'all', label: '全部' },
  { value: 'protagonist', label: '主角' },
  { value: 'supporting', label: '配角' },
  { value: 'antagonist', label: '反派' },
  { value: 'npc', label: '路人' },
]

function mapRoleLabel(role: string): Character['role'] {
  if (role === '主角' || role === 'protagonist') return 'protagonist'
  if (role === '反派' || role === 'antagonist') return 'antagonist'
  if (role === '路人' || role === 'npc') return 'npc'
  return 'supporting'
}

function getRoleLabel(role: string): string {
  const r = mapRoleLabel(role)
  if (r === 'protagonist') return '主角'
  if (r === 'antagonist') return '反派'
  if (r === 'npc') return '路人'
  return '配角'
}

function getAvatarGradient(role: string): string {
  const r = mapRoleLabel(role)
  if (r === 'protagonist')
    return 'linear-gradient(135deg, var(--xy-brand-500), var(--xy-brand-700))'
  if (r === 'antagonist') return 'linear-gradient(135deg, #7f1d1d, #991b1b)'
  if (r === 'npc') return 'linear-gradient(135deg, var(--xy-surface-3), var(--xy-surface-1))'
  return 'linear-gradient(135deg, var(--xy-brand-600), var(--xy-brand-400))'
}

// Map backend Character to display format
const characters = computed<Character[]>(() => {
  if (bibleStore.characters.length > 0) {
    return bibleStore.characters.map((c) => ({
      id: c.id,
      name: c.name,
      role: mapRoleLabel(c.role),
      roleLabel: getRoleLabel(c.role),
      description: c.description || '',
      personality: c.personality || '',
      background: c.background || '',
      tags: c.personality ? c.personality.split(/[,，]/).slice(0, 3) : [c.role],
      avatarGradient: getAvatarGradient(c.role),
      radarFill: 'rgba(124,108,191,0.10)',
      radarStroke: 'var(--xy-brand-500)',
      stats: estimateStats(c),
      chapterAppearances: (c as { chapterAppearances?: ChapterAppearance[] }).chapterAppearances || [],
      relations: (c as { relations?: CharacterRelation[] }).relations || [],
    }))
  }
  return []
})

const filteredCharacters = computed(() => {
  let result = characters.value

  if (activeFilter.value !== 'all') {
    result = result.filter((c) => c.role === activeFilter.value)
  }

  if (searchQuery.value.trim()) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(
      (c) => c.name.toLowerCase().includes(query) || c.description.toLowerCase().includes(query)
    )
  }

  // "出场频率"排序暂无后端数据支撑，保持原顺序（稳定排序）
  if (sortBy.value === 'freq') {
    result = [...result]
  }

  return result
})

function getRadarPoints(stats: Character['stats']): string {
  const { force, wisdom, charm, luck, background } = stats
  const centerX = 50
  const centerY = 50
  const maxRadius = 40

  const angles = [
    -Math.PI / 2,
    -Math.PI / 2 + (2 * Math.PI) / 5,
    -Math.PI / 2 + (4 * Math.PI) / 5,
    -Math.PI / 2 + (6 * Math.PI) / 5,
    -Math.PI / 2 + (8 * Math.PI) / 5,
  ]

  const values = [force, wisdom, charm, luck, background]

  return values
    .map((val, i) => {
      const r = (val / 100) * maxRadius
      const x = centerX + r * Math.cos(angles[i])
      const y = centerY + r * Math.sin(angles[i])
      return `${x.toFixed(1)},${y.toFixed(1)}`
    })
    .join(' ')
}

function selectCharacter(char: Character) {
  selectedCharacter.value = char
}

function closeDetail() {
  selectedCharacter.value = null
}

async function createNewCharacter() {
  const newId = characters.value.length + 1
  try {
    await bibleStore.createCharacter(novelId.value, {
      name: '新人物' + newId,
      role: '配角',
      description: '点击编辑人物信息',
      personality: '新人物',
    })
  } catch (e) {
    // If API fails, the fallback data won't update, but the UI won't crash
    console.error('Failed to create character:', e)
  }
}

// ===== 角色编辑/删除 =====
// 角色 role 选项（后端 character.role 存中文）
const roleOptions = [
  { label: '主角', value: '主角' },
  { label: '配角', value: '配角' },
  { label: '反派', value: '反派' },
  { label: '路人', value: '路人' },
]

const genderOptions = [
  { label: '男', value: '男' },
  { label: '女', value: '女' },
  { label: '其他', value: '其他' },
]

// 后端中文 role 与前端枚举的映射
function roleToBackend(role: Character['role']): string {
  if (role === 'protagonist') return '主角'
  if (role === 'antagonist') return '反派'
  if (role === 'npc') return '路人'
  return '配角'
}

const editModalVisible = ref(false)
const editSaving = ref(false)
const editForm = ref<{
  id: string
  name: string
  role: string
  description: string
  personality: string
  background: string
  gender: string
  age: string
}>({
  id: '',
  name: '',
  role: '配角',
  description: '',
  personality: '',
  background: '',
  gender: '',
  age: '',
})

function openEditModal(char: Character) {
  editForm.value = {
    id: String(char.id),
    name: char.name || '',
    role: roleToBackend(char.role),
    description: char.description || '',
    personality: char.personality || '',
    background: char.background || '',
    gender: char.gender || '',
    age: char.age || '',
  }
  editModalVisible.value = true
}

async function submitEdit() {
  if (!editForm.value.id || editSaving.value) return
  editSaving.value = true
  try {
    const { id, name, role, description, personality, background, gender, age } = editForm.value
    await bibleStore.updateCharacter(id, {
      name,
      role,
      description,
      personality,
      background,
      gender,
      age,
    })
    // 同步当前选中状态（characters computed 会随 store 数据自动重算）
    const updated = characters.value.find((c) => String(c.id) === id)
    if (updated && selectedCharacter.value && String(selectedCharacter.value.id) === id) {
      selectedCharacter.value = { ...updated }
    }
    editModalVisible.value = false
    toast.success('人物已更新')
  } catch (e) {
    console.error('Failed to update character:', e)
    toast.error('更新失败，请重试')
  } finally {
    editSaving.value = false
  }
}

async function handleDelete(char: Character) {
  if (!char.id) return
  if (!window.confirm(`确认删除人物「${char.name}」？此操作不可撤销。`)) return
  try {
    await bibleStore.deleteCharacter(String(char.id))
    if (selectedCharacter.value && String(selectedCharacter.value.id) === String(char.id)) {
      selectedCharacter.value = null
    }
    toast.success('人物已删除')
  } catch (e) {
    console.error('Failed to delete character:', e)
    toast.error('删除失败，请重试')
  }
}

onMounted(async () => {
  if (novelStore.novels.length === 0) {
    await novelStore.fetchNovels()
  }
  bibleStore.fetchCharacters(novelId.value)
})
</script>

<style scoped>
.characters-page {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background: var(--xy-bg-page);
  font-family: var(--xy-font-sans);
}

/* ========== Top Bar ========== */
.topbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: var(--xy-topbar-h);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;
  background: var(--xy-topbar-gradient);
  border-bottom: 1px solid var(--xy-border-1);
  z-index: var(--xy-z-nav-fixed);
}

.topbar-left {
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
  transition: all var(--xy-dur-sm) ease;
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

.brand-text {
  font-family: var(--xy-font-display);
  font-size: var(--xy-fs-lg);
  font-weight: 600;
  color: var(--xy-brand-700);
  letter-spacing: var(--xy-tracking-tight);
}

.page-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 2px 8px;
  font-size: var(--xy-fs-xs);
  font-weight: 500;
  background: var(--xy-brand-200);
  color: var(--xy-brand-700);
  border-radius: var(--xy-radius-sm);
}

.topbar-right {
  display: flex;
  align-items: center;
  gap: 16px;
}

.icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  color: var(--xy-text-2);
  cursor: pointer;
  padding: 4px;
  border-radius: var(--xy-radius-sm);
  transition: color var(--xy-dur-sm) ease;
}

.icon-btn:hover {
  color: var(--xy-text-1);
}

.icon {
  width: 16px;
  height: 16px;
}

.user-avatar {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--xy-fs-xs);
  font-weight: 500;
  border-radius: 50%;
  background: var(--xy-brand-400);
  color: var(--xy-text-inverse);
}

/* ========== Main Layout ========== */
.main-layout {
  display: flex;
  margin-top: var(--xy-topbar-h);
  margin-bottom: var(--xy-statusbar-h);
  height: calc(100vh - var(--xy-topbar-h) - var(--xy-statusbar-h));
}

.left-nav {
  width: 56px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: var(--xy-surface-1);
  border-right: 1px solid var(--xy-border-1);
}

.nav-list {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding-top: 12px;
  flex: 1;
}

.nav-item {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: var(--xy-radius-md);
  color: var(--xy-text-3);
  transition:
    background-color var(--xy-dur-sm) ease,
    color var(--xy-dur-sm) ease;
  text-decoration: none;
}

.nav-item:hover {
  color: var(--xy-text-2);
  background: var(--xy-surface-hover);
}

.nav-item-active {
  background: var(--xy-surface-active);
  color: var(--xy-brand-600);
}

.nav-icon {
  width: 16px;
  height: 16px;
}

/* ========== Content Area ========== */
.content-area {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* ========== Toolbar ========== */
.toolbar {
  height: var(--xy-toolbar-h);
  flex-shrink: 0;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 0 16px;
  background: var(--xy-surface-1);
  border-bottom: 1px solid var(--xy-border-1);
}

.toolbar-left {
  flex: 1;
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 8px;
}

.search-box {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 12px;
  height: 32px;
  max-width: 280px;
  flex: 1;
  background: var(--xy-surface-2);
  border: 1px solid var(--xy-border-1);
  border-radius: var(--xy-radius-md);
  transition:
    border-color var(--xy-dur-sm) ease,
    box-shadow var(--xy-dur-sm) ease;
}

.search-box:focus-within {
  border-color: var(--xy-border-focus);
  box-shadow: var(--xy-shadow-focus-ring);
}

.search-icon {
  width: 14px;
  height: 14px;
  flex-shrink: 0;
  color: var(--xy-text-3);
}

.search-input {
  flex: 1;
  min-width: 0;
  background: transparent;
  border: none;
  outline: none;
  font-size: var(--xy-fs-sm);
  color: var(--xy-text-1);
  font-family: var(--xy-font-sans);
  padding: 0;
}

.search-input::placeholder {
  color: var(--xy-text-3);
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
}

.filter-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 4px 10px;
  font-size: var(--xy-fs-xs);
  font-family: var(--xy-font-sans);
  background: var(--xy-surface-2);
  color: var(--xy-text-2);
  border: none;
  border-radius: var(--xy-radius-sm);
  cursor: pointer;
  white-space: nowrap;
  transition:
    background-color var(--xy-dur-sm) ease,
    color var(--xy-dur-sm) ease;
}

.filter-btn:hover {
  background: var(--xy-surface-hover);
  color: var(--xy-text-1);
}

.filter-btn-active {
  background: var(--xy-brand-400);
  color: var(--xy-text-inverse);
}

.filter-btn-active:hover {
  background: var(--xy-brand-400);
  color: var(--xy-text-inverse);
}

.sort-group {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-shrink: 0;
  color: var(--xy-text-3);
}

.sort-icon {
  width: 14px;
  height: 14px;
}

.sort-select {
  background: transparent;
  border: none;
  outline: none;
  font-size: var(--xy-fs-xs);
  color: var(--xy-text-2);
  font-family: var(--xy-font-sans);
  cursor: pointer;
}

.sort-select option {
  background: var(--xy-surface-2);
}

.btn-new {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  font-size: var(--xy-fs-xs);
  font-weight: 600;
  font-family: var(--xy-font-sans);
  background: var(--xy-brand-500);
  color: var(--xy-text-inverse);
  border: none;
  border-radius: var(--xy-radius-md);
  cursor: pointer;
  white-space: nowrap;
  flex-shrink: 0;
  transition:
    filter var(--xy-dur-sm) ease,
    transform var(--xy-dur-sm) ease;
}

.btn-new:hover {
  filter: brightness(1.1);
  transform: translateY(-1px);
}

.btn-new:active {
  transform: translateY(0);
  filter: brightness(1);
}

.btn-icon {
  width: 14px;
  height: 14px;
}

/* ========== Page Header ========== */
.page-header {
  padding: 20px 24px 12px;
  background: var(--xy-bg-canvas);
}

.title-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
}

.page-title {
  font-size: var(--xy-fs-2xl);
  font-weight: 600;
  color: var(--xy-text-1);
  margin: 0;
  letter-spacing: var(--xy-tracking-tight);
}

.count-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 24px;
  height: 24px;
  padding: 0 8px;
  border-radius: 12px;
  font-size: var(--xy-fs-sm);
  font-weight: 500;
  background: var(--xy-brand-100);
  color: var(--xy-brand-500);
}

/* ========== Character Grid ========== */
.character-grid {
  flex: 1;
  overflow-y: auto;
  padding: 0 24px 24px;
  background: var(--xy-bg-canvas);
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  align-content: start;
}

.character-card {
  background: var(--xy-surface-1);
  border: 1px solid var(--xy-border-1);
  border-radius: var(--xy-radius-lg);
  padding: 16px;
  cursor: pointer;
  transition:
    border-color var(--xy-dur-sm) ease,
    transform var(--xy-dur-sm) ease;
}

.character-card:hover {
  border-color: var(--xy-border-2);
  transform: translateY(-2px);
}

.card-header {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.avatar {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: var(--xy-fs-lg);
  font-weight: 600;
  border-radius: 50%;
  color: var(--xy-text-inverse);
  flex-shrink: 0;
}

.char-info {
  flex: 1;
  min-width: 0;
}

.name-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.char-name {
  font-size: var(--xy-fs-md);
  font-weight: 600;
  color: var(--xy-text-1);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.role-tag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 2px 6px;
  font-size: var(--xy-fs-xs);
  border-radius: var(--xy-radius-xs);
  flex-shrink: 0;
}

.role-protagonist {
  background: var(--xy-brand-200);
  color: var(--xy-brand-700);
}

.role-supporting {
  background: var(--xy-info-bg);
  color: var(--xy-info);
}

.role-antagonist {
  background: var(--xy-danger-bg);
  color: var(--xy-danger);
}

.role-npc {
  background: var(--xy-surface-2);
  color: var(--xy-text-3);
}

.char-desc {
  font-size: var(--xy-fs-xs);
  color: var(--xy-text-3);
  margin: 4px 0 0 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.tag-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 12px;
  flex-wrap: wrap;
}

.tag-item {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 2px 6px;
  font-size: var(--xy-fs-xs);
  background: var(--xy-surface-2);
  color: var(--xy-text-2);
  border-radius: var(--xy-radius-xs);
}

.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--xy-border-1);
}

.chapter-count {
  font-size: var(--xy-fs-xs);
  color: var(--xy-text-3);
}

.radar-chart svg {
  opacity: 0.85;
  transition: opacity var(--xy-dur-sm) ease;
}

.radar-chart:hover svg {
  opacity: 1;
}

/* ========== Status Bar ========== */
.statusbar {
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  height: var(--xy-statusbar-h);
  display: flex;
  align-items: center;
  padding: 0 16px;
  background: var(--xy-surface-1);
  border-top: 1px solid var(--xy-border-1);
}

.status-text {
  font-size: var(--xy-fs-xs);
  color: var(--xy-text-3);
}

.card-active {
  border-color: var(--xy-brand-400);
  box-shadow: 0 0 0 2px rgba(124, 108, 191, 0.2);
}

/* ========== Detail Drawer ========== */
.detail-drawer {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  left: 0;
  z-index: var(--xy-z-modal);
  display: flex;
  justify-content: flex-end;
}

.drawer-overlay {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.5);
  -webkit-backdrop-filter: blur(2px);
  backdrop-filter: blur(2px);
}

.drawer-content {
  position: relative;
  width: 420px;
  max-width: 90vw;
  background: var(--xy-surface-1);
  border-left: 1px solid var(--xy-border-1);
  display: flex;
  flex-direction: column;
  animation: drawer-slide-in 0.3s ease;
}

@keyframes drawer-slide-in {
  from {
    transform: translateX(100%);
  }
  to {
    transform: translateX(0);
  }
}

.drawer-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px;
  border-bottom: 1px solid var(--xy-border-1);
  position: relative;
}

.drawer-avatar {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  font-weight: 600;
  color: var(--xy-text-inverse);
  flex-shrink: 0;
}

.drawer-title-group {
  flex: 1;
  min-width: 0;
}

.drawer-title {
  font-size: 20px;
  font-weight: 600;
  color: var(--xy-text-1);
  margin: 0 0 4px 0;
}

.drawer-close {
  position: absolute;
  top: 16px;
  right: 16px;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  color: var(--xy-text-3);
  cursor: pointer;
  border-radius: var(--xy-radius-sm);
  transition:
    color var(--xy-dur-sm) ease,
    background var(--xy-dur-sm) ease;
}

.drawer-close:hover {
  color: var(--xy-text-1);
  background: var(--xy-surface-hover);
}

.close-icon {
  width: 16px;
  height: 16px;
}

.drawer-body {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.detail-section {
  margin-bottom: 24px;
}

.section-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--xy-text-1);
  margin: 0 0 12px 0;
}

.section-content {
  font-size: 14px;
  line-height: 1.7;
  color: var(--xy-text-2);
  margin: 0;
}

.empty-tip {
  font-size: 13px;
  color: var(--xy-text-4);
  margin: 0;
  font-style: italic;
}

.tag-item-lg {
  padding: 4px 10px;
  font-size: 13px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 8px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 12px 8px;
  background: var(--xy-surface-2);
  border-radius: var(--xy-radius-md);
}

.stat-label {
  font-size: 11px;
  color: var(--xy-text-3);
}

.stat-value {
  font-size: 18px;
  font-weight: 600;
  color: var(--xy-brand-600);
}

.info-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.info-item {
  display: flex;
  justify-content: space-between;
  padding: 10px 12px;
  background: var(--xy-surface-2);
  border-radius: var(--xy-radius-sm);
}

.info-label {
  font-size: 13px;
  color: var(--xy-text-3);
}

.info-value {
  font-size: 13px;
  font-weight: 500;
  color: var(--xy-text-1);
}

/* ========== Drawer Actions ========== */
.drawer-actions {
  display: flex;
  gap: 8px;
  padding-top: 16px;
  margin-top: 8px;
  border-top: 1px solid var(--xy-border-1);
}

.btn-edit,
.btn-delete {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  font-size: var(--xy-fs-sm);
  font-family: var(--xy-font-sans);
  font-weight: 500;
  border-radius: var(--xy-radius-md);
  border: 1px solid var(--xy-border-1);
  background: var(--xy-surface-1);
  color: var(--xy-text-2);
  cursor: pointer;
  transition:
    background-color var(--xy-dur-sm) ease,
    color var(--xy-dur-sm) ease,
    border-color var(--xy-dur-sm) ease;
}

.btn-edit:hover {
  background: var(--xy-brand-50, var(--xy-surface-hover));
  color: var(--xy-brand-600);
  border-color: var(--xy-brand-400);
}

.btn-delete {
  color: var(--xy-danger);
  border-color: var(--xy-border-1);
}

.btn-delete:hover {
  background: var(--xy-danger-bg, rgba(220, 38, 38, 0.1));
  border-color: var(--xy-danger);
}

/* ========== Modal Footer ========== */
.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

@media (max-width: 1200px) {
  .character-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .character-grid {
    grid-template-columns: 1fr;
  }

  .filter-group {
    display: none;
  }

  .sort-group {
    display: none;
  }
}

@media (prefers-reduced-motion: reduce) {
  .character-card,
  .btn-new,
  .filter-btn,
  .nav-item,
  .icon-btn {
    transition-duration: 0.01ms !important;
  }

  .radar-chart svg {
    transition-duration: 0.01ms !important;
  }
}
</style>
