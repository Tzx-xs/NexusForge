<template>
  <div class="writing-sidebar">
    <!-- AI 控制台覆盖层 -->
    <transition name="ai-slide">
      <div v-if="aiConsoleStore.visible" class="ai-console-overlay">
        <div class="ai-console-header">
          <span class="ai-console-title">AI 控制台</span>
          <button class="ai-close-btn" aria-label="收起 AI 控制台" @click="aiConsoleStore.close()">
            <span class="ai-close-icon" aria-hidden="true">&lsaquo;</span>
          </button>
        </div>
        <div class="ai-console-body">
          <AiConsole
            :content="chapterStore.currentChapter?.content || ''"
            :chapter-id="chapterId"
            :character-names="characterNames"
            :location-names="locationNames"
            @generated="handleGenerated"
          />
        </div>
      </div>
    </transition>

    <!-- 主导航 -->
    <div class="sidebar-header">
      <div class="sidebar-tabs">
        <button
          v-for="tab in tabs"
          :key="tab.key"
          class="sidebar-tab"
          :class="{ 'tab-active': activeTab === tab.key }"
          @click="activeTab = tab.key"
        >
          <component :is="tab.icon" class="tab-icon" />
          {{ tab.label }}
        </button>
      </div>
      <button
        class="ai-toggle-btn"
        :class="{ active: aiConsoleStore.visible }"
        :aria-label="aiConsoleStore.visible ? '收起 AI 控制台' : '打开 AI 控制台'"
        @click="aiConsoleStore.toggle()"
      >
        <Wand class="ai-toggle-icon" />
      </button>
    </div>

    <!-- 设定面板 -->
    <div v-show="activeTab === 'bible'" class="sidebar-body">
      <div class="bible-subtabs">
        <button
          v-for="sub in bibleSubs"
          :key="sub.key"
          class="bible-subtab"
          :class="{ active: bibleSubTab === sub.key }"
          @click="bibleSubTab = sub.key"
        >
          {{ sub.label }}
        </button>
      </div>

      <div class="bible-content">
        <div v-if="bibleSubTab === 'characters'" class="character-list">
          <div
            v-for="c in characters"
            :key="c.id"
            class="character-item"
            :class="{ active: isSelectedCharacter(c.id) }"
            @click="selectCharacter(c)"
          >
            <div class="char-avatar">{{ c.name.charAt(0) }}</div>
            <div class="char-info">
              <span class="char-name">{{ c.name }}</span>
              <span class="char-role">{{ c.role }}</span>
            </div>
          </div>
          <div v-if="characters.length === 0" class="empty-hint">暂无人物</div>
        </div>

        <div v-else class="setting-panel">
          <div class="category-list">
            <button
              v-for="cat in categories"
              :key="cat"
              class="category-chip"
              :class="{ active: activeCategory === cat }"
              @click="selectCategory(cat)"
            >
              {{ cat }}
            </button>
          </div>
          <div class="setting-list">
            <div
              v-for="s in settings"
              :key="s.id"
              class="setting-item"
              :class="{ active: isSelectedSetting(s.id) }"
              @click="selectSetting(s)"
            >
              <span class="setting-name">{{ s.name }}</span>
              <span class="setting-type">{{ settingTypeLabel(s.setting_type) }}</span>
            </div>
            <div v-if="settings.length === 0" class="empty-hint">暂无设定</div>
          </div>
        </div>
      </div>

      <div class="sidebar-footer">
        <button class="create-btn" @click="handleCreate">
          <Plus class="create-icon" />
          新建{{ bibleSubTab === 'characters' ? '人物' : '设定' }}
        </button>
      </div>
    </div>

    <!-- 大纲面板 -->
    <div v-show="activeTab === 'outline'" class="sidebar-body outline-body">
      <ChapterRail :novel-id="novelId" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useRoute } from 'vue-router'
import { Book, GitBranch, Wand, Plus } from '@vicons/tabler'
import { useBibleStore } from '@/stores/bible'
import { useChapterStore } from '@/stores/chapter'
import { useAiConsoleStore } from '@/stores/aiConsole'
import { useDocViewerStore } from '@/stores/docViewer'
import { useCurrentNovelId } from '@/composables/useCurrentNovelId'
import ChapterRail from './ChapterRail.vue'
import AiConsole from './AiConsole.vue'
import { toast } from '@/utils/toast'

const route = useRoute()
const bibleStore = useBibleStore()
const chapterStore = useChapterStore()
const aiConsoleStore = useAiConsoleStore()
const docViewerStore = useDocViewerStore()
const { novelId } = useCurrentNovelId()

const tabs = [
  { key: 'bible' as const, label: '设定', icon: Book },
  { key: 'outline' as const, label: '大纲', icon: GitBranch },
]
const activeTab = ref<'bible' | 'outline'>('outline')

const bibleSubs = [
  { key: 'characters' as const, label: '人物' },
  { key: 'settings' as const, label: '设定' },
]
const bibleSubTab = ref<'characters' | 'settings'>('characters')
const activeCategory = ref('')

const chapterId = computed(() => (route.params.chapterId as string) || undefined)
const characters = computed(() => bibleStore.characters)
const settings = computed(() => bibleStore.settings)
const categories = ref(['地理', '势力', '修炼体系', '历史', '物品'])

const characterNames = computed(() => bibleStore.characters.map((c) => c.name))
const locationNames = computed(() =>
  bibleStore.settings.filter((s) => s.setting_type === 'location').map((s) => s.name)
)

const settingTypeMap: Record<string, string> = {
  world: '世界',
  worldview: '世界观',
  location: '地点',
  item: '物品',
  faction: '势力',
  system: '体系',
  history: '历史',
}

function settingTypeLabel(type: string): string {
  return settingTypeMap[type] || type
}

function isSelectedCharacter(id: string): boolean {
  return docViewerStore.selectedType === 'character' && docViewerStore.selectedId === id
}

function isSelectedSetting(id: string): boolean {
  return docViewerStore.selectedType === 'setting' && docViewerStore.selectedId === id
}

function selectCharacter(c: (typeof characters.value)[number]) {
  docViewerStore.selectCharacter(c)
}

function selectSetting(s: (typeof settings.value)[number]) {
  docViewerStore.selectSetting(s)
}

function selectCategory(cat: string) {
  activeCategory.value = cat
  bibleStore.fetchSettings(novelId.value, cat)
}

async function handleCreate() {
  if (bibleSubTab.value === 'characters') {
    try {
      await bibleStore.createCharacter(novelId.value, { name: '新人物', role: '配角' })
      await bibleStore.fetchCharacters(novelId.value)
      toast.success('人物已创建')
    } catch (e) {
      console.error(e)
      toast.error('创建失败')
    }
  } else {
    const cat = activeCategory.value || categories.value[0]
    try {
      await bibleStore.createSetting(novelId.value, {
        name: '新设定',
        setting_type: cat,
        description: '',
      })
      await bibleStore.fetchSettings(novelId.value, cat)
      toast.success('设定已创建')
    } catch (e) {
      console.error(e)
      toast.error('创建失败')
    }
  }
}

function handleGenerated(generated: string) {
  const cid = chapterId.value
  if (!cid || !generated) return
  aiConsoleStore.close()
  chapterStore
    .updateChapter(cid, { content: generated })
    .then(() => toast.success('生成内容已写入章节'))
    .catch(() => toast.error('写入失败'))
}

watch(
  () => novelId.value,
  (nid) => {
    if (nid) {
      bibleStore.fetchCharacters(nid)
      const cat = activeCategory.value || categories.value[0]
      bibleStore.fetchSettings(nid, cat)
    }
  },
  { immediate: true }
)

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape' && aiConsoleStore.visible) {
    aiConsoleStore.close()
  }
}

onMounted(() => {
  document.addEventListener('keydown', handleKeydown)
  if (novelId.value) {
    bibleStore.fetchCharacters(novelId.value)
    const cat = activeCategory.value || categories.value[0]
    bibleStore.fetchSettings(novelId.value, cat)
  }
})

onUnmounted(() => {
  document.removeEventListener('keydown', handleKeydown)
})
</script>

<style scoped>
.writing-sidebar {
  position: relative;
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  background: var(--xy-surface-1);
  overflow: hidden;
}

/* ========== AI 控制台覆盖层 ========== */
.ai-console-overlay {
  position: absolute;
  inset: 0;
  z-index: 20;
  display: flex;
  flex-direction: column;
  background: var(--xy-surface-1);
  box-shadow: 8px 0 32px rgba(0, 0, 0, 0.35);
}

.ai-console-header {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 var(--xy-space-3);
  height: var(--xy-panel-header-h, 44px);
  border-bottom: var(--xy-border-w-1) solid var(--xy-border-1);
  background: linear-gradient(180deg, var(--xy-surface-2) 0%, var(--xy-surface-1) 100%);
}

.ai-console-title {
  font-size: var(--xy-fs-sm);
  font-weight: var(--xy-fw-sb);
  color: var(--xy-text-1);
  letter-spacing: 0.01em;
}

.ai-close-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border: none;
  border-radius: var(--xy-radius-sm);
  background: transparent;
  color: var(--xy-text-3);
  cursor: pointer;
  transition: all var(--xy-dur-sm) var(--xy-ease-standard);
}

.ai-close-btn > * {
  pointer-events: none;
}

.ai-close-btn:hover {
  background: var(--xy-surface-hover);
  color: var(--xy-text-1);
}

.ai-close-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px;
  height: 16px;
  font-size: 22px;
  line-height: 16px;
  pointer-events: none;
}

.ai-console-body {
  flex: 1;
  overflow: hidden;
}

.ai-slide-enter-active,
.ai-slide-leave-active {
  transition: transform 0.25s var(--xy-ease-standard, ease), opacity 0.25s ease;
}

.ai-slide-enter-from,
.ai-slide-leave-to {
  transform: translateX(-100%);
  opacity: 0;
}

/* ========== 侧边栏头部 ========== */
.sidebar-header {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--xy-space-2);
  padding: var(--xy-space-2);
  border-bottom: var(--xy-border-w-1) solid var(--xy-border-1);
  background: var(--xy-surface-1);
}

.sidebar-tabs {
  display: flex;
  align-items: center;
  flex: 1;
  gap: var(--xy-space-1);
  padding: 2px;
  background: var(--xy-surface-2);
  border-radius: var(--xy-radius-md);
  border: var(--xy-border-w-1) solid var(--xy-border-1);
}

.sidebar-tab {
  flex: 1;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  height: 28px;
  padding: 0 var(--xy-space-3);
  border: none;
  border-radius: var(--xy-radius-sm);
  background: transparent;
  color: var(--xy-text-3);
  font-size: var(--xy-fs-xs);
  font-weight: var(--xy-fw-med);
  cursor: pointer;
  transition: all var(--xy-dur-sm) var(--xy-ease-standard);
}

.sidebar-tab:hover {
  color: var(--xy-text-2);
}

.sidebar-tab.tab-active {
  background: linear-gradient(135deg, var(--xy-brand-500), var(--xy-brand-600));
  color: var(--xy-brand-starlight);
  box-shadow: 0 2px 8px rgba(124, 108, 191, 0.28);
}

.tab-icon {
  width: 13px;
  height: 13px;
}

.ai-toggle-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border: var(--xy-border-w-1) solid var(--xy-border-1);
  border-radius: var(--xy-radius-md);
  background: var(--xy-surface-2);
  color: var(--xy-text-3);
  cursor: pointer;
  transition: all var(--xy-dur-sm) var(--xy-ease-standard);
  flex-shrink: 0;
}

.ai-toggle-btn:hover {
  border-color: var(--xy-brand-300);
  color: var(--xy-brand-500);
  background: var(--xy-brand-50);
}

.ai-toggle-btn.active {
  border-color: var(--xy-brand-500);
  background: linear-gradient(135deg, var(--xy-brand-500), var(--xy-brand-600));
  color: var(--xy-brand-starlight);
}

.ai-toggle-icon {
  width: 15px;
  height: 15px;
}

/* ========== 内容区 ========== */
.sidebar-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  min-height: 0;
}

.outline-body {
  padding: 0;
}

.bible-subtabs {
  display: flex;
  align-items: center;
  gap: var(--xy-space-1);
  padding: var(--xy-space-2) var(--xy-space-3);
  border-bottom: var(--xy-border-w-1) solid var(--xy-border-1);
}

.bible-subtab {
  flex: 1;
  height: 26px;
  border: none;
  border-radius: var(--xy-radius-sm);
  background: transparent;
  color: var(--xy-text-3);
  font-size: var(--xy-fs-xs);
  cursor: pointer;
  transition: all var(--xy-dur-sm) ease;
}

.bible-subtab:hover {
  color: var(--xy-text-2);
  background: var(--xy-surface-hover);
}

.bible-subtab.active {
  background: var(--xy-surface-active);
  color: var(--xy-brand-600);
  font-weight: var(--xy-fw-med);
}

.bible-content {
  flex: 1;
  overflow-y: auto;
  padding: var(--xy-space-2);
}

.character-list,
.setting-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.character-item,
.setting-item {
  display: flex;
  align-items: center;
  gap: var(--xy-space-2);
  padding: var(--xy-space-2);
  border-radius: var(--xy-radius-sm);
  cursor: pointer;
  transition: background-color 150ms ease;
}

.character-item:hover,
.setting-item:hover {
  background: var(--xy-surface-hover);
}

.character-item.active,
.setting-item.active {
  background: var(--xy-brand-50);
}

.character-item.active .char-name,
.setting-item.active .setting-name {
  color: var(--xy-brand-600);
  font-weight: var(--xy-fw-med);
}

/* ========== 设定面板 ========== */
.setting-panel {
  display: flex;
  flex-direction: column;
  gap: var(--xy-space-2);
}

.category-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--xy-space-1);
  padding-bottom: var(--xy-space-2);
  border-bottom: var(--xy-border-w-1) solid var(--xy-border-1);
}

.category-chip {
  padding: 4px 10px;
  border: var(--xy-border-w-1) solid var(--xy-border-1);
  border-radius: var(--xy-radius-sm);
  background: var(--xy-surface-1);
  color: var(--xy-text-3);
  font-size: var(--xy-fs-xs);
  cursor: pointer;
  transition: all 150ms ease;
}

.category-chip:hover {
  background: var(--xy-surface-hover);
  color: var(--xy-text-2);
}

.category-chip.active {
  background: var(--xy-brand-500);
  border-color: var(--xy-brand-500);
  color: var(--xy-text-inverse);
}

.setting-item {
  justify-content: space-between;
}

.setting-name {
  flex: 1;
  min-width: 0;
  font-size: var(--xy-fs-sm);
  color: var(--xy-text-1);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.setting-type {
  flex-shrink: 0;
  padding: 1px 6px;
  border-radius: var(--xy-radius-xs);
  background: var(--xy-surface-2);
  color: var(--xy-text-3);
  font-size: 10px;
}

.char-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: var(--xy-brand-300);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: var(--xy-fw-sb);
  color: white;
  flex-shrink: 0;
}

.char-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.char-name {
  font-size: var(--xy-fs-sm);
  color: var(--xy-text-1);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.char-role {
  font-size: 11px;
  color: var(--xy-text-3);
}

.empty-hint {
  padding: var(--xy-space-8) var(--xy-space-2);
  text-align: center;
  color: var(--xy-text-4);
  font-size: var(--xy-fs-xs);
}

.sidebar-footer {
  flex-shrink: 0;
  padding: var(--xy-space-3);
  border-top: var(--xy-border-w-1) solid var(--xy-border-1);
}

.create-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: var(--xy-space-2);
  width: 100%;
  height: 32px;
  border: 1px dashed var(--xy-border-2);
  border-radius: var(--xy-radius-sm);
  background: transparent;
  color: var(--xy-text-3);
  font-size: var(--xy-fs-sm);
  cursor: pointer;
  transition: all 150ms ease;
}

.create-btn:hover {
  border-color: var(--xy-brand-500);
  color: var(--xy-brand-600);
  background: var(--xy-brand-50);
}

.create-icon {
  width: 14px;
  height: 14px;
}
</style>
