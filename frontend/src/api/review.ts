import request from './http'

export interface ReviewDetail {
  type: string
  severity: string
  description: string
  location?: string
  suggestion?: string
}

export interface ReviewResult {
  id: string
  chapter_id: string
  total_score: number
  grade: string
  red_line_violations: string[]
  dimension_scores: Record<string, number>
  review_details: ReviewDetail[]
  created_at: string
}

export interface ReviewTask {
  id: string
  title: string
  novel_id: string | null
  status: 'pending' | 'completed' | 'failed' | string
  result: string
  created_at: string
  updated_at: string
}

export interface ReviewTaskList {
  items: ReviewTask[]
  total: number
  page: number
  page_size: number
}

export function getReview(chapterId: string) {
  return request.get<ReviewResult | null>(`/chapters/${chapterId}/review`)
}

export function reviewChapter(chapterId: string) {
  return request.post<ReviewResult>(`/chapters/${chapterId}/review`)
}

export function listReviewTasks(page = 1, pageSize = 20) {
  return request.get<ReviewTaskList>(`/reviews?page=${page}&page_size=${pageSize}`)
}

export function createReviewTask(title: string, novelId?: string) {
  return request.post<ReviewTask>(`/reviews`, { title, novel_id: novelId || null })
}

export function getReviewTask(taskId: string) {
  return request.get<ReviewTask>(`/reviews/${taskId}`)
}

export function updateReviewTask(
  taskId: string,
  payload: { status?: string; result?: string }
) {
  return request.put<ReviewTask>(`/reviews/${taskId}`, payload)
}

export function deleteReviewTask(taskId: string) {
  return request.delete<{ deleted: boolean }>(`/reviews/${taskId}`)
}
