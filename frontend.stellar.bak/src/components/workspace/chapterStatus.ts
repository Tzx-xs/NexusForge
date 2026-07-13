/**
 * Sprint 1.5 GREEN：章节状态映射工具。
 *
 * 后端真实状态值（见 backend/domain/chapter_status.py ChapterStatus 枚举）：
 *   - "draft"      创建态
 *   - "planned"    已生成章纲
 *   - "completed"  已完成正文
 *
 * 已删除的状态：
 *   - "generated"  历史死状态，被立刻覆盖为 completed（Sprint 1 已删除）
 *   - "published"/"writing"/"current"  前端旧期待，后端从未写入
 *
 * 前端三态（用于 UI 样式区分）：
 *   - draft       草稿（灰）
 *   - planned     已规划（蓝/橙）
 *   - completed   已完成（绿）
 */

/** 后端可能下发的状态字符串 */
export type BackendStatus = 'draft' | 'planned' | 'completed' | string

/** 前端用于 UI 样式的状态键 */
export type ChapterStatusKey = 'draft' | 'planned' | 'completed'

/**
 * 将后端 status 字符串映射为前端 UI 状态键。
 *
 * 规则：
 *   draft      -> draft
 *   planned    -> planned（不再降级为 draft）
 *   completed  -> completed
 *   其他/未知  -> draft（防御）
 */
export function mapStatus(status: BackendStatus | undefined | null): ChapterStatusKey {
  if (status === 'draft') return 'draft'
  if (status === 'planned') return 'planned'
  if (status === 'completed') return 'completed'
  // 历史值（published/writing/current/generated）与未知值统一降级为 draft
  return 'draft'
}
