import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Chapter } from '@/api/chapters'
import type { Character, WorldSetting } from '@/api/bible'

export type DocType = 'chapter' | 'character' | 'setting'

const settingTypeMap: Record<string, string> = {
  world: '世界',
  worldview: '世界观',
  location: '地点',
  item: '物品',
  faction: '势力',
  system: '体系',
  history: '历史',
}

function formatCharacterContent(c: Character): string {
  const parts: string[] = [`# ${c.name}`]
  if (c.role) parts.push(`\n**角色：** ${c.role}`)
  if (c.gender) parts.push(`**性别：** ${c.gender}`)
  if (c.age) parts.push(`**年龄：** ${c.age}`)
  if (c.description) parts.push(`\n## 简介\n\n${c.description}`)
  if (c.personality) parts.push(`## 性格\n\n${c.personality}`)
  if (c.background) parts.push(`## 背景\n\n${c.background}`)
  if (c.appearance) parts.push(`## 外貌\n\n${c.appearance}`)
  return parts.join('\n')
}

export const useDocViewerStore = defineStore('docViewer', () => {
  const selectedType = ref<DocType | null>(null)
  const selectedId = ref<string | null>(null)
  const title = ref('')
  const content = ref('')
  const mode = ref<'markdown' | 'plain'>('markdown')

  const hasSelection = computed(() => !!selectedType.value && !!selectedId.value)

  function selectChapter(chapter: Chapter) {
    selectedType.value = 'chapter'
    selectedId.value = chapter.id
    title.value = chapter.title ? `第${chapter.number}章 ${chapter.title}` : `第${chapter.number}章`
    content.value = chapter.content || ''
    mode.value = 'plain'
  }

  function selectCharacter(character: Character) {
    selectedType.value = 'character'
    selectedId.value = character.id
    title.value = character.name
    content.value = formatCharacterContent(character)
    mode.value = 'markdown'
  }

  function selectSetting(setting: WorldSetting) {
    selectedType.value = 'setting'
    selectedId.value = setting.id
    const typeLabel = settingTypeMap[setting.setting_type] || setting.setting_type
    title.value = `${setting.name} · ${typeLabel}`
    content.value = setting.description || ''
    mode.value = 'markdown'
  }

  function clear() {
    selectedType.value = null
    selectedId.value = null
    title.value = ''
    content.value = ''
    mode.value = 'markdown'
  }

  return {
    selectedType,
    selectedId,
    title,
    content,
    mode,
    hasSelection,
    selectChapter,
    selectCharacter,
    selectSetting,
    clear,
  }
})
