import request from './http'

export interface Foreshadow {
  id: string
  novel_id: string
  title: string
  description: string
  priority: string
  status: string
  planted_chapter_id: string | null
  planted_chapter_index: number | null
  resolved_chapter_id: string | null
  resolved_chapter_index: number | null
  related_characters: string[]
  related_locations: string[]
  urgency: string
  tags: string[]
  notes: string | null
  created_at: string
  updated_at: string
}

export interface PendingReport {
  total_pending: number
  high_priority: number
  overdue_threshold: number
  foreshadows: Foreshadow[]
}

export function getForeshadowList(novelId: string, status?: string, priority?: string) {
  const params: Record<string, string | undefined> = {}
  if (status) params.status = status
  if (priority) params.priority = priority
  return request.get<Foreshadow[]>(`/novels/${novelId}/foreshadows`, { params })
}

export function getForeshadow(foreshadowId: string) {
  return request.get<Foreshadow>(`/foreshadows/${foreshadowId}`)
}

export function createForeshadow(
  novelId: string,
  data: {
    title: string
    description?: string
    priority?: string
    status?: string
    planted_chapter_index?: number
    related_characters?: string[]
    related_locations?: string[]
    urgency?: string
    tags?: string[]
    notes?: string
  }
) {
  return request.post<Foreshadow>(`/novels/${novelId}/foreshadows`, data)
}

export function updateForeshadow(foreshadowId: string, data: Partial<Foreshadow>) {
  return request.put<Foreshadow>(`/foreshadows/${foreshadowId}`, data)
}

export function deleteForeshadow(foreshadowId: string) {
  return request.delete(`/foreshadows/${foreshadowId}`)
}

export function getPendingReport(novelId: string) {
  return request.get<PendingReport>(`/novels/${novelId}/foreshadows/pending-report`)
}
