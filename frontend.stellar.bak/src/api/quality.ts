import request from './http'

export interface GuardIssue {
  guard_name: string
  severity: string
  category: string
  message: string
  paragraph_index?: number
  char_offset?: number
  char_length?: number
  suggestion: string
  location?: Record<string, unknown>
}

export interface GuardResult {
  guard_name: string
  passed: boolean
  score: number
  issues: GuardIssue[]
  duration_ms: number
  metadata: Record<string, unknown>
}

export interface AuditReport {
  overall_score: number
  passed: boolean
  total_issues: number
  critical_issues: number
  duration_ms: number
  guard_results: GuardResult[]
  metadata: Record<string, unknown>
}

export interface GuardInfo {
  name: string
  description: string
  weight: number
}

export interface AuditRequest {
  content: string
  context?: Record<string, unknown>
  enabled_guards?: string[]
}

export function listGuards() {
  return request.get<GuardInfo[]>('/quality/guards')
}

export function runAudit(requestData: AuditRequest) {
  return request.post<AuditReport>('/quality/audit', requestData)
}

export function auditChapter(chapterId: string, requestData?: AuditRequest) {
  return request.post<AuditReport>(`/quality/chapters/${chapterId}/audit`, requestData || {})
}
