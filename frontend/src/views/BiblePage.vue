<template>
  <div class="bible-wrap">
    <div v-if="draftDetected" class="draft-banner">
      <n-card size="small" :bordered="true">
        <div class="draft-card-body">
          <div class="draft-card-info">
            <n-icon :component="Inbox" :size="20" color="var(--xy-brand-500)" />
            <span class="draft-card-text">
              检测到向导扩展字段（{{ draftFieldCount }} 项），是否导入为设定？
            </span>
          </div>
          <div class="draft-card-actions">
            <n-button size="small" :loading="importing" type="primary" @click="handleImportDraft">
              导入
            </n-button>
            <n-button size="small" :disabled="importing" @click="handleIgnoreDraft">
              忽略
            </n-button>
          </div>
        </div>
      </n-card>
    </div>
    <div class="bible-page">
      <div class="bible-sidebar">
        <div class="sidebar-tabs">
          <div
            class="tab-item"
            :class="{ active: activeTab === 'characters' }"
            @click="activeTab = 'characters'"
          >
            人物
          </div>
          <div
            class="tab-item"
            :class="{ active: activeTab === 'settings' }"
            @click="activeTab = 'settings'"
          >
            设定
          </div>
        </div>
        <div class="sidebar-content">
          <div v-if="activeTab === 'characters'" class="character-list">
            <div
              v-for="c in characters"
              :key="c.id"
              class="character-item"
              :class="{ active: selectedCharacter?.id === c.id }"
              @click="selectCharacter(c)"
            >
              <div class="avatar">{{ c.name.charAt(0) }}</div>
              <div class="info">
                <span class="name">{{ c.name }}</span>
                <span class="role">{{ c.role }}</span>
              </div>
            </div>
          </div>
          <div v-else class="setting-list">
            <div
              v-for="cat in categories"
              :key="cat"
              class="setting-category"
              :class="{ active: activeCategory === cat }"
              @click="selectCategory(cat)"
            >
              {{ cat }}
            </div>
          </div>
        </div>
        <div class="sidebar-footer">
          <n-button block type="primary" size="small" @click="handleCreate">
            <template #icon>
              <n-icon :component="Plus" />
            </template>
            新建
          </n-button>
        </div>
      </div>
      <div class="bible-main">
        <div v-if="selectedCharacter" class="detail-panel">
          <h2 class="detail-title">{{ selectedCharacter.name }}</h2>
          <p class="detail-role">{{ selectedCharacter.role }}</p>
          <div class="detail-content">
            <p>{{ selectedCharacter.description || '暂无详细描述，点击编辑添加人物信息...' }}</p>
          </div>
          <div class="detail-actions">
            <n-button size="small" type="primary" @click="openCharacterEdit(selectedCharacter)">
              <template #icon>
                <n-icon :component="Edit" />
              </template>
              编辑
            </n-button>
            <n-button
              size="small"
              type="error"
              ghost
              @click="handleDeleteCharacter(selectedCharacter)"
            >
              <template #icon>
                <n-icon :component="Trash" />
              </template>
              删除
            </n-button>
          </div>
        </div>
        <div v-else-if="activeCategory" class="detail-panel">
          <h2 class="detail-title">{{ activeCategory }}</h2>
          <div class="detail-content">
            <div v-if="settingsLoading" class="loading-state">加载中...</div>
            <div v-else-if="categorySettings.length === 0" class="empty-category">
              该分类暂无设定，点击新建创建
            </div>
            <div v-else class="setting-items">
              <div v-for="s in categorySettings" :key="s.id" class="setting-item">
                <div class="setting-item-info">
                  <div class="setting-name">{{ s.name }}</div>
                  <div class="setting-desc">{{ s.description || '暂无描述' }}</div>
                </div>
                <div class="setting-item-actions">
                  <n-button size="tiny" quaternary @click.stop="openSettingEdit(s)">
                    <template #icon>
                      <n-icon :component="Edit" />
                    </template>
                  </n-button>
                  <n-button
                    size="tiny"
                    quaternary
                    type="error"
                    @click.stop="handleDeleteSetting(s)"
                  >
                    <template #icon>
                      <n-icon :component="Trash" />
                    </template>
                  </n-button>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div v-else class="empty-state">
          <n-icon :component="Book" :size="48" color="#4e4768" />
          <p>选择一个条目查看详情</p>
        </div>
      </div>

      <!-- 人物编辑弹窗 -->
      <n-modal
        v-model:show="characterEditVisible"
        preset="card"
        title="编辑人物"
        style="width: 480px; max-width: 92vw"
      >
        <n-form :model="characterEditForm" label-placement="top">
          <n-form-item label="姓名">
            <n-input v-model:value="characterEditForm.name" placeholder="请输入姓名" />
          </n-form-item>
          <n-form-item label="角色类型">
            <n-select v-model:value="characterEditForm.role" :options="roleOptions" />
          </n-form-item>
          <n-form-item label="描述">
            <n-input
              v-model:value="characterEditForm.description"
              type="textarea"
              :autosize="{ minRows: 2 }"
              placeholder="请输入描述"
            />
          </n-form-item>
          <n-form-item label="性格">
            <n-input
              v-model:value="characterEditForm.personality"
              type="textarea"
              :autosize="{ minRows: 2 }"
              placeholder="请输入性格"
            />
          </n-form-item>
          <n-form-item label="背景">
            <n-input
              v-model:value="characterEditForm.background"
              type="textarea"
              :autosize="{ minRows: 2 }"
              placeholder="请输入背景"
            />
          </n-form-item>
        </n-form>
        <template #footer>
          <div class="modal-footer">
            <n-button @click="characterEditVisible = false">取消</n-button>
            <n-button type="primary" :loading="characterSaving" @click="submitCharacterEdit">
              保存
            </n-button>
          </div>
        </template>
      </n-modal>

      <!-- 设定编辑弹窗 -->
      <n-modal
        v-model:show="settingEditVisible"
        preset="card"
        title="编辑设定"
        style="width: 480px; max-width: 92vw"
      >
        <n-form :model="settingEditForm" label-placement="top">
          <n-form-item label="名称">
            <n-input v-model:value="settingEditForm.name" placeholder="请输入名称" />
          </n-form-item>
          <n-form-item label="分类">
            <n-select v-model:value="settingEditForm.setting_type" :options="settingTypeOptions" />
          </n-form-item>
          <n-form-item label="描述">
            <n-input
              v-model:value="settingEditForm.description"
              type="textarea"
              :autosize="{ minRows: 3 }"
              placeholder="请输入描述"
            />
          </n-form-item>
        </n-form>
        <template #footer>
          <div class="modal-footer">
            <n-button @click="settingEditVisible = false">取消</n-button>
            <n-button type="primary" :loading="settingSaving" @click="submitSettingEdit">
              保存
            </n-button>
          </div>
        </template>
      </n-modal>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { useBibleStore } from '@/stores/bible'
import {
  NButton,
  NIcon,
  NCard,
  NModal,
  NForm,
  NFormItem,
  NInput,
  NSelect,
  useMessage,
} from 'naive-ui'
import { Plus, Book, Inbox, Edit, Trash } from '@vicons/tabler'
import type { WorldSetting } from '@/api/bible'

const route = useRoute()
const bibleStore = useBibleStore()
const message = useMessage()

const activeTab = ref('characters')
const activeCategory = ref('')
const characters = computed(() => {
  if (bibleStore.characters.length > 0) {
    return bibleStore.characters.map((c) => ({
      id: c.id,
      name: c.name,
      role: c.role,
      description: c.description,
      personality: c.personality,
      background: c.background,
    }))
  }
  return []
})

type CharacterItem = (typeof characters.value)[number]
const selectedCharacter = ref<CharacterItem | null>(null)

// 角色 role 选项（后端 character.role 存中文）
const roleOptions = [
  { label: '主角', value: '主角' },
  { label: '配角', value: '配角' },
  { label: '反派', value: '反派' },
  { label: '路人', value: '路人' },
]
const settingTypeOptions = [
  { label: '地理', value: '地理' },
  { label: '势力', value: '势力' },
  { label: '修炼体系', value: '修炼体系' },
  { label: '历史', value: '历史' },
  { label: '物品', value: '物品' },
]

// ===== 人物编辑 =====
const characterEditVisible = ref(false)
const characterSaving = ref(false)
const characterEditForm = ref<{
  id: string
  name: string
  role: string
  description: string
  personality: string
  background: string
}>({
  id: '',
  name: '',
  role: '配角',
  description: '',
  personality: '',
  background: '',
})

function openCharacterEdit(c: CharacterItem) {
  characterEditForm.value = {
    id: c.id,
    name: c.name || '',
    role: c.role || '配角',
    description: c.description || '',
    personality: c.personality || '',
    background: c.background || '',
  }
  characterEditVisible.value = true
}

async function submitCharacterEdit() {
  if (!characterEditForm.value.id || characterSaving.value) return
  characterSaving.value = true
  try {
    const { id, name, role, description, personality, background } = characterEditForm.value
    const updated = await bibleStore.updateCharacter(id, {
      name,
      role,
      description,
      personality,
      background,
    })
    // 同步本地选中状态（characters computed 已被 store 数据驱动，更新后自动重算）
    selectedCharacter.value = {
      id: updated.id,
      name: updated.name,
      role: updated.role,
      description: updated.description,
      personality: updated.personality,
      background: updated.background,
    }
    characterEditVisible.value = false
    message.success('人物已更新')
  } catch (e) {
    console.error('Failed to update character:', e)
    message.error('更新失败，请重试')
  } finally {
    characterSaving.value = false
  }
}

async function handleDeleteCharacter(c: CharacterItem) {
  if (!c.id) return
  if (!window.confirm(`确认删除人物「${c.name}」？此操作不可撤销。`)) return
  try {
    await bibleStore.deleteCharacter(c.id)
    selectedCharacter.value = null
    message.success('人物已删除')
  } catch (e) {
    console.error('Failed to delete character:', e)
    message.error('删除失败，请重试')
  }
}

// ===== 设定编辑 =====
const settingEditVisible = ref(false)
const settingSaving = ref(false)
const settingEditForm = ref<{
  id: string
  name: string
  setting_type: string
  description: string
}>({
  id: '',
  name: '',
  setting_type: '地理',
  description: '',
})

function openSettingEdit(s: WorldSetting) {
  settingEditForm.value = {
    id: s.id,
    name: s.name || '',
    setting_type: s.setting_type || '地理',
    description: s.description || '',
  }
  settingEditVisible.value = true
}

async function submitSettingEdit() {
  if (!settingEditForm.value.id || settingSaving.value) return
  settingSaving.value = true
  try {
    const { id, name, setting_type, description } = settingEditForm.value
    await bibleStore.updateSetting(id, { name, setting_type, description })
    // 切换到目标分类并刷新
    if (activeCategory.value !== setting_type) {
      activeCategory.value = setting_type
      await bibleStore.fetchSettings(novelId.value, setting_type)
    } else {
      await bibleStore.fetchSettings(novelId.value, setting_type)
    }
    settingEditVisible.value = false
    message.success('设定已更新')
  } catch (e) {
    console.error('Failed to update setting:', e)
    message.error('更新失败，请重试')
  } finally {
    settingSaving.value = false
  }
}

async function handleDeleteSetting(s: WorldSetting) {
  if (!s.id) return
  if (!window.confirm(`确认删除设定「${s.name}」？此操作不可撤销。`)) return
  try {
    await bibleStore.deleteSetting(s.id)
    await bibleStore.fetchSettings(novelId.value, activeCategory.value)
    message.success('设定已删除')
  } catch (e) {
    console.error('Failed to delete setting:', e)
    message.error('删除失败，请重试')
  }
}

const categories = ref(['地理', '势力', '修炼体系', '历史', '物品'])

const novelId = computed(() => String(route.params.novelId || '1'))
const categorySettings = computed(() => bibleStore.settings)
const settingsLoading = computed(() => bibleStore.loading)

// 草稿导入（来自 NewBookWizard 的 localStorage 扩展字段）
interface NovelDraft {
  era?: string
  worldType?: string
  powerSystem?: string
  socialStructure?: string
  locations?: string
  protagonistName?: string
  protagonistPersonality?: string
  protagonistBackground?: string
  supportingCharacters?: string
}
const draftDetected = ref(false)
const draftFieldCount = ref(0)
const draftData = ref<NovelDraft | null>(null)
const importing = ref(false)

const draftFields: Array<keyof NovelDraft> = [
  'era',
  'worldType',
  'powerSystem',
  'socialStructure',
  'locations',
  'protagonistName',
  'protagonistPersonality',
  'protagonistBackground',
  'supportingCharacters',
]

function draftKey() {
  return `xy-novel-draft-${novelId.value}`
}

function checkDraft() {
  try {
    const raw = localStorage.getItem(draftKey())
    if (!raw) return
    const data = JSON.parse(raw) as NovelDraft
    const count = draftFields.filter((f) => data[f] && String(data[f]).trim()).length
    if (count === 0) {
      localStorage.removeItem(draftKey())
      return
    }
    draftData.value = data
    draftFieldCount.value = count
    draftDetected.value = true
  } catch (e) {
    console.error('Failed to parse novel draft:', e)
    localStorage.removeItem(draftKey())
  }
}

async function handleImportDraft() {
  if (!draftData.value || importing.value) return
  importing.value = true
  try {
    const d = draftData.value
    const nid = novelId.value
    // 设定类字段 → createSetting
    const settingEntries: Array<[string, string, string]> = []
    if (d.era && d.era.trim()) settingEntries.push(['时代背景', '历史', d.era])
    if (d.worldType && d.worldType.trim()) settingEntries.push(['世界类型', '地理', d.worldType])
    if (d.powerSystem && d.powerSystem.trim())
      settingEntries.push(['修炼体系', '修炼体系', d.powerSystem])
    if (d.socialStructure && d.socialStructure.trim())
      settingEntries.push(['社会结构', '势力', d.socialStructure])
    if (d.locations && d.locations.trim()) settingEntries.push(['地理位置', '地理', d.locations])
    for (const [name, type, desc] of settingEntries) {
      await bibleStore.createSetting(nid, { name, setting_type: type, description: desc })
    }
    // 主角 → createCharacter
    if (d.protagonistName && d.protagonistName.trim()) {
      await bibleStore.createCharacter(nid, {
        name: d.protagonistName,
        role: '主角',
        personality: d.protagonistPersonality || '',
        background: d.protagonistBackground || '',
      })
    }
    // 配角列表 → 存为一条设定
    if (d.supportingCharacters && d.supportingCharacters.trim()) {
      await bibleStore.createSetting(nid, {
        name: '配角列表',
        setting_type: 'character',
        description: d.supportingCharacters,
      })
    }
    localStorage.removeItem(draftKey())
    draftDetected.value = false
    draftData.value = null
    await bibleStore.fetchCharacters(nid)
    if (activeCategory.value) {
      await bibleStore.fetchSettings(nid, activeCategory.value)
    }
    message.success('草稿已导入设定与人物')
  } catch (e) {
    console.error('Failed to import draft:', e)
    message.error('导入失败，请重试')
  } finally {
    importing.value = false
  }
}

function handleIgnoreDraft() {
  localStorage.removeItem(draftKey())
  draftDetected.value = false
  draftData.value = null
  message.info('已忽略草稿')
}

function selectCharacter(char: CharacterItem) {
  selectedCharacter.value = char
  activeCategory.value = ''
}

function selectCategory(cat: string) {
  activeCategory.value = cat
  selectedCharacter.value = null
  bibleStore.fetchSettings(novelId.value, cat)
}

async function handleCreate() {
  if (activeTab.value === 'settings') {
    if (!activeCategory.value) {
      activeCategory.value = categories.value[0]
    }
    try {
      await bibleStore.createSetting(novelId.value, {
        name: '新设定',
        setting_type: activeCategory.value,
        description: '',
      })
      await bibleStore.fetchSettings(novelId.value, activeCategory.value)
    } catch (e) {
      console.error('Failed to create setting:', e)
    }
  } else if (activeTab.value === 'characters') {
    try {
      await bibleStore.createCharacter(novelId.value, {
        name: '新人物',
        role: '配角',
      })
      await bibleStore.fetchCharacters(novelId.value)
    } catch (e) {
      console.error('Failed to create character:', e)
    }
  }
}

watch(activeTab, (newTab) => {
  if (newTab === 'settings' && activeCategory.value) {
    bibleStore.fetchSettings(novelId.value, activeCategory.value)
  }
})

onMounted(() => {
  bibleStore.fetchCharacters(novelId.value)
  checkDraft()
})
</script>

<style scoped>
.bible-wrap {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.draft-banner {
  padding: 12px 16px;
  border-bottom: 1px solid var(--xy-border-1);
  background: var(--xy-surface-1);
  flex-shrink: 0;
}

.draft-card-body {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.draft-card-info {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}

.draft-card-text {
  font-size: 13px;
  color: var(--xy-text-1);
}

.draft-card-actions {
  display: flex;
  gap: 8px;
  flex-shrink: 0;
}

.bible-page {
  display: flex;
  flex: 1;
  min-height: 0;
}

.bible-sidebar {
  width: 240px;
  border-right: 1px solid var(--xy-border-1);
  background: var(--xy-surface-1);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
}

.sidebar-tabs {
  display: flex;
  padding: 8px;
  gap: 4px;
  border-bottom: 1px solid var(--xy-border-1);
}

.tab-item {
  flex: 1;
  padding: 8px;
  text-align: center;
  font-size: 13px;
  color: var(--xy-text-2);
  border-radius: var(--xy-radius-sm);
  cursor: pointer;
  transition:
    background-color 150ms ease,
    color 150ms ease;
}

.tab-item:hover {
  background: var(--xy-surface-hover);
}

.tab-item.active {
  background: var(--xy-surface-active);
  color: var(--xy-brand-500);
  font-weight: 500;
}

.sidebar-content {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.character-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: var(--xy-radius-sm);
  cursor: pointer;
  transition: background-color 150ms ease;
}

.character-item:hover {
  background: var(--xy-surface-hover);
}

.character-item.active {
  background: var(--xy-brand-50);
}

.avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--xy-brand-300);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  font-weight: 600;
  color: white;
  flex-shrink: 0;
}

.info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.name {
  font-size: 13px;
  color: var(--xy-text-1);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.role {
  font-size: 11px;
  color: var(--xy-text-3);
}

.setting-category {
  padding: 8px 10px;
  font-size: 13px;
  color: var(--xy-text-2);
  border-radius: var(--xy-radius-sm);
  cursor: pointer;
  transition: background-color 150ms ease;
}

.setting-category:hover {
  background: var(--xy-surface-hover);
}

.setting-category.active {
  background: var(--xy-brand-50);
  color: var(--xy-brand-600);
}

.sidebar-footer {
  padding: 12px;
  border-top: 1px solid var(--xy-border-1);
}

.bible-main {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--xy-bg-canvas);
  min-width: 0;
}

.detail-panel {
  width: 100%;
  max-width: 600px;
  padding: 32px;
  background: var(--xy-surface-1);
  border-radius: var(--xy-radius-lg);
  border: 1px solid var(--xy-border-1);
}

.detail-title {
  font-size: 24px;
  font-weight: 600;
  color: var(--xy-text-1);
  margin: 0 0 8px 0;
}

.detail-role {
  font-size: 14px;
  color: var(--xy-brand-500);
  margin: 0 0 24px 0;
}

.detail-content {
  font-size: 14px;
  line-height: 1.8;
  color: var(--xy-text-2);
}

.loading-state {
  padding: 24px;
  text-align: center;
  color: var(--xy-text-3);
}

.empty-category {
  padding: 24px;
  text-align: center;
  color: var(--xy-text-3);
}

.setting-items {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.setting-item {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  padding: 12px;
  border: 1px solid var(--xy-border-1);
  border-radius: var(--xy-radius-sm);
}

.setting-item-info {
  flex: 1;
  min-width: 0;
}

.setting-item-actions {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

.setting-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--xy-text-1);
  margin-bottom: 4px;
}

.setting-desc {
  font-size: 13px;
  color: var(--xy-text-3);
}

.detail-actions {
  display: flex;
  gap: 8px;
  margin-top: 24px;
  padding-top: 16px;
  border-top: 1px solid var(--xy-border-1);
}

.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  color: var(--xy-text-3);
}

.empty-state p {
  margin: 0;
  font-size: 14px;
}
</style>
