import request from './http'

export interface AutoWriteSession {
  session_id: string
  novel_id: string
  state: string
  current_chapter_index: number
  total_chapters_completed: number
  total_words_generated: number
  failed_chapters: number[]
  current_progress: number
  started_at?: number
  updated_at?: number
  error?: string
  mode: string
  target_chapters: number
}

export function createSession(data: {
  novel_id: string
  target_chapters?: number
  min_quality_score?: number
  max_retries_per_chapter?: number
  pause_between_chapters?: boolean
  auto_rewrite_on_fail?: boolean
  mode?: string
}) {
  return request.post<AutoWriteSession>('/autonomous/sessions', data)
}

export function listSessions(novelId?: string) {
  const url = novelId ? `/autonomous/sessions?novel_id=${novelId}` : '/autonomous/sessions'
  return request.get<AutoWriteSession[]>(url)
}

export function getSession(sessionId: string) {
  return request.get<AutoWriteSession>(`/autonomous/sessions/${sessionId}`)
}

export function startSession(sessionId: string) {
  return request.post<AutoWriteSession>(`/autonomous/sessions/${sessionId}/start`)
}

export function pauseSession(sessionId: string) {
  return request.post<AutoWriteSession>(`/autonomous/sessions/${sessionId}/pause`)
}

export function resumeSession(sessionId: string) {
  return request.post<AutoWriteSession>(`/autonomous/sessions/${sessionId}/resume`)
}

export function cancelSession(sessionId: string) {
  return request.post<{ cancelled: boolean }>(`/autonomous/sessions/${sessionId}/cancel`)
}
