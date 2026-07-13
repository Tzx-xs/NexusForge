/**
 * Sprint 5.3: Agent 面板可见性 store。
 *
 * 跨组件共享 AgentChatPanel 的显示状态,
 * 支持 Home 页面卡片点击 → query 参数同步 → WorkspaceShell 打开面板。
 */
import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useAgentPanelStore = defineStore('agentPanel', () => {
  const visible = ref(false)

  function open() {
    visible.value = true
  }

  function close() {
    visible.value = false
  }

  function toggle() {
    visible.value = !visible.value
  }

  return { visible, open, close, toggle }
})
