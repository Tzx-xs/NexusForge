import request from './http'
import type { AxiosRequestConfig } from 'axios'

export interface Novel {
  id: string
  title: string
  premise: string
  genre: string
  target_chapters: number
  current_chapter: number
  cover_url: string
  style_tags: string[]
  perspective: string
  created_at: string
  updated_at: string
}

export interface NovelListResult {
  items: Novel[]
  total: number
  page: number
  page_size: number
}

export function getNovelList(params?: { page: number; page_size: number }) {
  return request.get<NovelListResult>('/novels', { params })
}

export function getNovel(id: string) {
  return request.get<Novel>(`/novels/${id}`)
}

export function createNovel(
  data: {
    title: string
    premise: string
    genre: string
    target_chapters: number
    style_tags?: string[]
    perspective?: string
    cover_url?: string
  },
  config?: AxiosRequestConfig
) {
  return request.post<Novel>('/novels', data, config)
}

export function updateNovel(id: string, data: Partial<Novel>) {
  return request.put<Novel>(`/novels/${id}`, data)
}

export function deleteNovel(id: string, config?: AxiosRequestConfig) {
  return request.delete(`/novels/${id}`, config)
}

export interface NovelStats {
  novel_id: string
  title: string
  chapter_count: number
  completed_chapters: number
  total_words: number
  target_chapters: number
  completion_rate: number
  today_words?: number
  streak_days?: number
  total_chapters?: number
}

export function getNovelStats(id: string) {
  return request.get<NovelStats>(`/novels/${id}/stats`)
}
