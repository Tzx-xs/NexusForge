import { defineStore } from 'pinia'
import { ref } from 'vue'

/**
 * AI 控制台覆盖层状态
 *
 * 用途：
 * - 在写作页左侧边栏上方弹出 AI 控制台（生成 / 质检 / 文风 / 铁锁 / 伏笔 / 历史）。
 * - 支持 WritingSidebar 内部按钮、顶部工具栏按钮或其他组件统一打开/收起。
 */
export const useAiConsoleStore = defineStore('aiConsole', () => {
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
