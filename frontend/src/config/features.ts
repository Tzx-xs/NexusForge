type EnvValue = string | boolean | undefined

function envFlag(value: EnvValue): boolean {
  if (typeof value === 'boolean') return value
  if (typeof value !== 'string') return false
  return ['1', 'true', 'yes', 'on', 'enabled'].includes(value.trim().toLowerCase())
}

const aiInvocationDebug = envFlag(import.meta.env.VITE_ENABLE_AI_INVOCATION_DEBUG)
// Phase 4 Task 4.1：Tiptap 富文本编辑器（默认关闭，渐进式启用）
const tiptapEditor = envFlag(import.meta.env.VITE_ENABLE_TIPTAP_EDITOR)

export const featureFlags = Object.freeze({
  aiInvocationDebug,
  variableCenterDebugPanels: aiInvocationDebug,
  tiptapEditor,
})

export type FeatureFlags = typeof featureFlags
