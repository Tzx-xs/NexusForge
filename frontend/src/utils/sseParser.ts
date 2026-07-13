/** 统一的 SSE (Server-Sent Events) 解析器。
 *
 * 从 4 个文件（aiSuggest.ts, agent.ts, useAiGenerate.ts, AiConsole.vue）的
 * 内联 parseSseBlocks 提取而来，消除重复代码。
 */

export interface SseEvent {
  /** SSE 事件类型，如 token / complete / error，默认为 'message' */
  event: string
  /** 事件携带的数据（JSON 字符串） */
  data: string
}

/**
 * 将 SSE 文本流按 \\n\\n 分割为事件块，解析 event: 和 data: 字段。
 *
 * @param text 原始 SSE 文本（已去除 \\r）
 * @returns 解析后的事件数组
 */
export function parseSseBlocks(text: string): SseEvent[] {
  const events: SseEvent[] = []
  const lines = text.split('\n')
  let currentEvent = ''
  let currentData = ''

  for (const line of lines) {
    if (line.startsWith('event: ')) {
      currentEvent = line.slice(7).trim()
    } else if (line.startsWith('data: ')) {
      currentData = line.slice(6)
    } else if (line.trim() === '' && currentData) {
      events.push({ event: currentEvent || 'message', data: currentData })
      currentEvent = ''
      currentData = ''
    }
  }
  // 处理末尾无空行的情况
  if (currentData) {
    events.push({ event: currentEvent || 'message', data: currentData })
  }
  return events
}
