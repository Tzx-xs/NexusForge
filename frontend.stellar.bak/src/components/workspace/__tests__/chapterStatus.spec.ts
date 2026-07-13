/**
 * Sprint 1.4 RED：章节状态映射的失败测试。
 *
 * 验证：
 * - mapStatus 不再降级 "planned" 为 draft（用户生成 outline 后状态应是 planned）
 * - 删除对 "published"/"writing"/"current" 等后端从未写入值的期待
 * - 未知状态默认 draft（防御）
 */
import { describe, it, expect } from 'vitest'
import { mapStatus, type ChapterStatusKey } from '../chapterStatus'

describe('mapStatus', () => {
  it('draft 状态保持 draft', () => {
    expect(mapStatus('draft')).toBe('draft')
  })

  it('planned 状态映射为 planned（不再降级为 draft）', () => {
    // 这是 Sprint 1 的核心修复点：之前 planned 被降级为 draft
    expect(mapStatus('planned')).toBe('planned')
  })

  it('completed 状态映射为 completed', () => {
    expect(mapStatus('completed')).toBe('completed')
  })

  it('未知状态默认 draft（防御）', () => {
    expect(mapStatus('unknown')).toBe('draft')
    expect(mapStatus('')).toBe('draft')
  })

  it('不再期待后端从未写入的 "published" 状态', () => {
    // 后端代码中 "published" 状态零命中，前端不应期待
    // 改为默认 draft
    expect(mapStatus('published')).toBe('draft')
  })

  it('不再期待后端从未写入的 "writing" / "current" 状态', () => {
    // 后端代码中 "writing"/"current" 状态零命中
    expect(mapStatus('writing')).toBe('draft')
    expect(mapStatus('current')).toBe('draft')
  })

  it('不再期待 "generated" 死状态（已被后端删除）', () => {
    // Sprint 1 后端已删除 "generated" 死状态，前端不应再识别
    expect(mapStatus('generated')).toBe('draft')
  })

  it('ChapterStatusKey 类型包含 planned', () => {
    const key: ChapterStatusKey = 'planned'
    expect(key).toBe('planned')
  })
})
