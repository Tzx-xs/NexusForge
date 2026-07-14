<template>
  <div class="command-overlay" @click.self="$emit('close')">
    <div class="command-palette">
      <div class="command-input-wrap">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="11" cy="11" r="8" />
          <path d="m21 21-4.35-4.35" />
        </svg>
        <input
          ref="inputRef"
          v-model="query"
          class="command-input"
          type="text"
          placeholder="搜索笔记、执行命令..."
          @keydown.escape="$emit('close')"
          @keydown.down="moveSelection(1)"
          @keydown.up="moveSelection(-1)"
          @keydown.enter="executeSelection"
        />
        <kbd class="command-esc">ESC</kbd>
      </div>

      <div class="command-results" v-if="filteredResults.length > 0">
        <button
          v-for="(item, index) in filteredResults"
          :key="item.id"
          class="command-item"
          :class="{ active: selectedIndex === index }"
          @click="executeItem(item)"
          @mouseenter="selectedIndex = index"
        >
          <span class="command-icon" v-html="item.icon"></span>
          <span class="command-label">{{ item.label }}</span>
          <span class="command-hint" v-if="item.hint">{{ item.hint }}</span>
        </button>
      </div>

      <div class="command-empty" v-else-if="query">
        <p>没有找到匹配的结果</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'

const emit = defineEmits<{ close: [] }>()
const router = useRouter()

const inputRef = ref<HTMLInputElement>()
const query = ref('')
const selectedIndex = ref(0)

interface CommandItem {
  id: string
  label: string
  icon: string
  hint?: string
  action: () => void
}

const commands: CommandItem[] = [
  {
    id: 'new-note',
    label: '新建笔记',
    icon: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>',
    hint: '⌘N',
    action: () => console.log('new note'),
  },
  {
    id: 'import',
    label: '导入 Markdown 文件',
    icon: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>',
    action: () => console.log('import'),
  },
  {
    id: 'settings',
    label: '打开设置',
    icon: '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="3"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>',
    action: () => router.push('/settings'),
  },
]

const filteredResults = computed(() => {
  if (!query.value) return commands
  const q = query.value.toLowerCase()
  return commands.filter(c => c.label.toLowerCase().includes(q))
})

function moveSelection(delta: number) {
  const len = filteredResults.value.length
  if (len === 0) return
  selectedIndex.value = (selectedIndex.value + delta + len) % len
}

function executeSelection() {
  const item = filteredResults.value[selectedIndex.value]
  if (item) executeItem(item)
}

function executeItem(item: CommandItem) {
  item.action()
  emit('close')
}

// 查询变化时重置选中索引，防止越界
watch(query, () => {
  selectedIndex.value = 0
})

onMounted(async () => {
  await nextTick()
  inputRef.value?.focus()
})
</script>

<style scoped>
.command-overlay {
  position: fixed;
  inset: 0;
  z-index: 1000;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  padding-top: 20vh;
}
.command-palette {
  width: 100%;
  max-width: 520px;
  background: var(--nexus-surface);
  border: 1px solid var(--nexus-border);
  border-radius: var(--nexus-radius-lg);
  box-shadow: var(--nexus-shadow-lg);
  overflow: hidden;
}
.command-input-wrap {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--nexus-border);
  color: var(--nexus-text-secondary);
}
.command-input {
  flex: 1;
  background: none;
  border: none;
  outline: none;
  color: var(--nexus-text);
  font-size: 14px;
  font-family: inherit;
}
.command-input::placeholder {
  color: var(--nexus-text-tertiary);
}
.command-esc {
  font-size: 11px;
  padding: 2px 6px;
  background: var(--nexus-bg);
  border: 1px solid var(--nexus-border);
  border-radius: 4px;
  color: var(--nexus-text-tertiary);
  font-family: inherit;
}
.command-results {
  max-height: 300px;
  overflow-y: auto;
  padding: 4px;
}
.command-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 8px 12px;
  border: none;
  background: transparent;
  color: var(--nexus-text-secondary);
  border-radius: var(--nexus-radius-sm);
  cursor: pointer;
  font-size: 13px;
  text-align: left;
  transition: background 0.1s ease;
}
.command-item:hover,
.command-item.active {
  background: var(--nexus-bg-hover);
  color: var(--nexus-text);
}
.command-icon {
  display: flex;
  align-items: center;
  color: var(--nexus-text-tertiary);
}
.command-label {
  flex: 1;
}
.command-hint {
  font-size: 11px;
  color: var(--nexus-text-tertiary);
}
.command-empty {
  padding: 24px;
  text-align: center;
  color: var(--nexus-text-tertiary);
  font-size: 13px;
}
</style>
