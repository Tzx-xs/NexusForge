import { defineStore } from 'pinia'
import { ref, inject, watch, type Ref } from 'vue'

/**
 * 侧栏折叠状态 store
 *
 * 用途：
 * - collapsed / toggle / setCollapsed：WorkspaceShell 的 Menu2 按钮切换 ChapterRail 折叠/展开。
 * - appSidebarCollapsed / toggleAppSidebar / setAppSidebarCollapsed：AppLayout 全局侧边栏折叠状态。
 * 持久化到 localStorage，与 theme/saveStatus 模式一致。
 */
export const useSidebarStore = defineStore('sidebar', () => {
  // Workspace ChapterRail 折叠状态（默认展开）
  const persisted = localStorage.getItem('xy-sidebar-collapsed')
  const collapsed = ref(persisted === 'true')

  // AppLayout 全局侧边栏折叠状态（默认展开）
  const appPersisted = localStorage.getItem('xy-app-sidebar-collapsed')
  const appSidebarCollapsed = ref(appPersisted === 'true')

  // 移动端检测 — 移动端默认折叠
  const isMobile = inject<Ref<boolean>>('isMobile') ?? ref(false)
  watch(isMobile, (val) => { if (val) collapsed.value = true })

  function toggle() {
    collapsed.value = !collapsed.value
    localStorage.setItem('xy-sidebar-collapsed', String(collapsed.value))
  }

  function setCollapsed(v: boolean) {
    collapsed.value = v
    localStorage.setItem('xy-sidebar-collapsed', String(v))
  }

  function toggleAppSidebar() {
    appSidebarCollapsed.value = !appSidebarCollapsed.value
    localStorage.setItem('xy-app-sidebar-collapsed', String(appSidebarCollapsed.value))
  }

  function setAppSidebarCollapsed(v: boolean) {
    appSidebarCollapsed.value = v
    localStorage.setItem('xy-app-sidebar-collapsed', String(v))
  }

  return {
    collapsed,
    toggle,
    setCollapsed,
    appSidebarCollapsed,
    toggleAppSidebar,
    setAppSidebarCollapsed,
    isMobile,
  }
})
