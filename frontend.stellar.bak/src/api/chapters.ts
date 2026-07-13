import request, { API_BASE_URL, getAuthHeaders } from './http'
import type { AxiosRequestConfig } from 'axios'

export interface Chapter {
  id: string
  novel_id: string
  number: number
  title: string
  outline: string
  content: string
  status: string
  word_count: number
  tension_score: number
  created_at: string
  updated_at: string
}

export function getChapterList(novelId: string, config?: AxiosRequestConfig) {
  return request.get<Chapter[]>(`/novels/${novelId}/chapters`, config)
}

export function getChapter(chapterId: string, config?: AxiosRequestConfig) {
  return request.get<Chapter>(`/chapters/${chapterId}`, config)
}

export function createChapter(novelId: string, data: { title: string; number?: number }) {
  return request.post<Chapter>(`/novels/${novelId}/chapters`, data)
}

export function updateChapter(
  chapterId: string,
  data: Partial<Pick<Chapter, 'title' | 'outline' | 'content' | 'status' | 'tension_score'>>
) {
  return request.put<Chapter>(`/chapters/${chapterId}`, data)
}

export function deleteChapter(chapterId: string) {
  return request.delete(`/chapters/${chapterId}`)
}

export function generateOutline(chapterId: string) {
  return request.post<Chapter>(`/chapters/${chapterId}/generate-outline`)
}

export function getGenerateContentUrl(chapterId: string): string {
  return `${API_BASE_URL}/chapters/${chapterId}/generate-content`
}

export { getAuthHeaders }
